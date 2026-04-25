#!/usr/bin/env python3
"""Collect self-play LedgerShield candidates and falsifier preferences."""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

try:  # pragma: no cover - supports direct script execution
    from .common import (
        DEFAULT_REWARD_WEIGHTS,
        EXISTING_SFT_DIR,
        EXQUISITE_ROOT,
        environment_reward,
        failure_reason,
        load_db,
        load_sft_examples,
        parse_completion,
        prompt_for_generation,
        rel_path,
        run_actions,
        split_examples,
        sft,
        to_jsonable,
        utc_now,
        write_csv,
        write_json,
        write_jsonl,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        DEFAULT_REWARD_WEIGHTS,
        EXISTING_SFT_DIR,
        EXQUISITE_ROOT,
        environment_reward,
        failure_reason,
        load_db,
        load_sft_examples,
        parse_completion,
        prompt_for_generation,
        rel_path,
        run_actions,
        split_examples,
        sft,
        to_jsonable,
        utc_now,
        write_csv,
        write_json,
        write_jsonl,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect LedgerShield self-play candidates.")
    parser.add_argument("--output-dir", type=Path, default=EXQUISITE_ROOT / "selfplay-0.5b")
    parser.add_argument("--sft-artifact-dir", type=Path, default=EXISTING_SFT_DIR)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--adapter-path", type=Path, default=EXISTING_SFT_DIR / "final_model")
    parser.add_argument("--case-limit", type=int, default=21)
    parser.add_argument("--eval-case-limit", type=int, default=9)
    parser.add_argument("--num-generations", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=2600)
    parser.add_argument("--temperature", type=float, default=0.85)
    parser.add_argument("--top-p", type=float, default=0.92)
    parser.add_argument("--seed", type=int, default=29)
    parser.add_argument(
        "--mode",
        choices=["model", "teacher-bootstrap", "smoke"],
        default="model",
        help="model uses Transformers generation; teacher-bootstrap/smoke avoid GPU dependencies.",
    )
    return parser.parse_args()


def load_model_generator(args: argparse.Namespace) -> Any:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Model self-play requires transformers, torch, and peft. Use --mode smoke for a local dependency-free check."
        ) from exc

    set_seed(int(args.seed))
    tokenizer = AutoTokenizer.from_pretrained(args.model, token=os.environ.get("HF_TOKEN") or None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        token=os.environ.get("HF_TOKEN") or None,
    )
    if args.adapter_path and args.adapter_path.exists():
        model = PeftModel.from_pretrained(model, str(args.adapter_path))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        model.to(device)
    model.eval()

    def generate(prompt: str, candidate_index: int) -> str:
        input_text = prompt_for_generation(prompt)
        inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {key: value.to(next(model.parameters()).device) for key, value in inputs.items()}
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=int(args.max_new_tokens),
                do_sample=True,
                temperature=float(args.temperature),
                top_p=float(args.top_p),
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        prompt_length = inputs["input_ids"].shape[-1]
        return tokenizer.decode(output_ids[0][prompt_length:], skip_special_tokens=True).strip()

    return generate


def teacher_bootstrap_completions(example: dict[str, Any], num_generations: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(f"selfplay::{seed}::{(example.get('metadata') or {}).get('case_id')}")
    completions: list[tuple[str, str]] = []
    teacher = str(example.get("teacher_completion") or example.get("completion") or "")
    compact = str(example.get("completion") or teacher)
    completions.append((teacher, "teacher_replay"))
    if compact and compact != teacher:
        completions.append((compact, "compact_teacher"))
    completions.append((json.dumps({"actions": [sft.naive_pay_action()]}, sort_keys=True), "naive_pay"))
    completions.append((json.dumps({"actions": sft.random_baseline_actions(example)}, sort_keys=True), "seeded_random"))
    actions, ok, _ = parse_completion(teacher)
    while len(completions) < num_generations:
        mutated = list(actions)
        if mutated and rng.random() < 0.55:
            mutated = mutated[:-1]
        if mutated and rng.random() < 0.35:
            rng.shuffle(mutated)
        if rng.random() < 0.30:
            mutated.append(sft.fallback_review_action("bootstrap_mutation_needs_review"))
        if not ok or not mutated:
            mutated = [sft.fallback_review_action("bootstrap_empty_plan")]
        completions.append((json.dumps({"actions": mutated}, sort_keys=True), "teacher_mutation"))
    return completions[:num_generations]


def build_preference_pair(group: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(group) < 2:
        return None
    ranked = sorted(group, key=lambda row: float(row.get("env_reward", -1.0)), reverse=True)
    best = ranked[0]
    worst = ranked[-1]
    if best.get("candidate_id") == worst.get("candidate_id"):
        return None
    return {
        "case_id": best.get("case_id"),
        "prompt": best.get("prompt"),
        "chosen": best.get("completion"),
        "rejected": worst.get("completion"),
        "chosen_reward": best.get("env_reward"),
        "rejected_reward": worst.get("env_reward"),
        "reward_margin": round(float(best.get("env_reward", 0.0)) - float(worst.get("env_reward", 0.0)), 6),
        "chosen_candidate_id": best.get("candidate_id"),
        "rejected_candidate_id": worst.get("candidate_id"),
        "chosen_failure_reason": best.get("failure_reason"),
        "rejected_failure_reason": worst.get("failure_reason"),
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(int(args.seed))
    db = load_db()
    examples = load_sft_examples(args.sft_artifact_dir)[: max(0, int(args.case_limit))]
    train_examples, eval_examples = split_examples(examples, int(args.eval_case_limit), int(args.seed))
    target_examples = eval_examples or examples
    generator = None if args.mode in {"teacher-bootstrap", "smoke"} else load_model_generator(args)

    write_jsonl(args.output_dir / "train_examples.jsonl", train_examples)
    write_jsonl(args.output_dir / "eval_examples.jsonl", target_examples)

    candidates: list[dict[str, Any]] = []
    preferences: list[dict[str, Any]] = []
    for example_index, example in enumerate(target_examples, start=1):
        metadata = example.get("metadata") or {}
        case_id = str(metadata.get("case_id") or "")
        prompt = str(example.get("prompt") or "")
        if not case_id or not prompt:
            continue
        if generator is None:
            completions = teacher_bootstrap_completions(example, int(args.num_generations), int(args.seed))
        else:
            completions = [
                (generator(prompt, candidate_index), "model_sample")
                for candidate_index in range(int(args.num_generations))
            ]
        group: list[dict[str, Any]] = []
        for candidate_index, (completion, source) in enumerate(completions):
            actions, parse_success, parse_error = parse_completion(completion)
            if not actions:
                actions = [sft.fallback_review_action(parse_error or "selfplay_no_actions")]
            result = run_actions(
                case_id,
                actions,
                db,
                parse_success=parse_success,
                parse_error=parse_error,
            )
            env_reward, reward_components = environment_reward(result, DEFAULT_REWARD_WEIGHTS)
            row = {
                "candidate_id": f"{case_id}::{candidate_index:02d}",
                "case_id": case_id,
                "task_type": metadata.get("task_type", ""),
                "example_index": example_index,
                "candidate_index": candidate_index,
                "generation_source": source,
                "prompt": prompt,
                "completion": completion,
                "actions": actions,
                "parse_success": parse_success,
                "parse_error": parse_error,
                "result": result,
                "env_reward": env_reward,
                "reward_components": reward_components,
                "failure_reason": failure_reason(result),
                "collected_at": utc_now(),
            }
            group.append(row)
        ranked_ids = [row["candidate_id"] for row in sorted(group, key=lambda row: row["env_reward"], reverse=True)]
        for row in group:
            row["candidate_rank"] = ranked_ids.index(row["candidate_id"]) + 1
            row["group_size"] = len(group)
            row["best_in_group"] = row["candidate_rank"] == 1
            candidates.append(row)
        pair = build_preference_pair(group)
        if pair:
            preferences.append(pair)
        print(
            f"[selfplay] {example_index}/{len(target_examples)} case={case_id} "
            f"best={max(row['env_reward'] for row in group):.4f} "
            f"worst={min(row['env_reward'] for row in group):.4f}",
            flush=True,
        )

    summary_rows = [
        {
            "case_id": row["case_id"],
            "candidate_id": row["candidate_id"],
            "candidate_rank": row["candidate_rank"],
            "env_reward": row["env_reward"],
            "score": row["result"].get("score"),
            "certificate_score": row["result"].get("certificate_score"),
            "unsafe_release": row["result"].get("unsafe_release"),
            "parse_success": row["parse_success"],
            "failure_reason": row["failure_reason"],
            "generation_source": row["generation_source"],
        }
        for row in candidates
    ]
    write_jsonl(args.output_dir / "selfplay_candidates.jsonl", candidates)
    write_jsonl(args.output_dir / "falsifier_preferences.jsonl", preferences)
    write_csv(args.output_dir / "selfplay_candidates.csv", summary_rows)
    config = {
        "generated_at": utc_now(),
        "mode": args.mode,
        "model": args.model,
        "adapter_path": rel_path(args.adapter_path),
        "sft_artifact_dir": rel_path(args.sft_artifact_dir),
        "case_count": len(target_examples),
        "candidate_count": len(candidates),
        "preference_pair_count": len(preferences),
        "num_generations": int(args.num_generations),
        "reward_weights": DEFAULT_REWARD_WEIGHTS,
        "outputs": {
            "selfplay_candidates": rel_path(args.output_dir / "selfplay_candidates.jsonl"),
            "falsifier_preferences": rel_path(args.output_dir / "falsifier_preferences.jsonl"),
        },
    }
    write_json(args.output_dir / "config.json", config)
    write_json(args.output_dir / "selfplay_summary.json", config)
    print(json.dumps(to_jsonable(config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
