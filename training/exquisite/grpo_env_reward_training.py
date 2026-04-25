#!/usr/bin/env python3
"""Environment-reward GRPO training for LedgerShield."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import random
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import (
        DEFAULT_REWARD_WEIGHTS,
        EXISTING_SFT_DIR,
        EXQUISITE_ROOT,
        environment_reward,
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
    parser = argparse.ArgumentParser(description="Train LedgerShield policy with GRPO environment rewards.")
    parser.add_argument("--output-dir", type=Path, default=EXQUISITE_ROOT / "grpo-0.5b")
    parser.add_argument("--sft-artifact-dir", type=Path, default=EXISTING_SFT_DIR)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--sft-adapter-path", type=Path, default=EXISTING_SFT_DIR / "final_model")
    parser.add_argument("--no-sft-adapter", action="store_true", help="Start GRPO from the base model instead of an SFT adapter.")
    parser.add_argument("--case-limit", type=int, default=45)
    parser.add_argument("--eval-case-limit", type=int, default=9)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=8e-6)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-prompt-length", type=int, default=2048)
    parser.add_argument("--max-completion-length", type=int, default=1800)
    parser.add_argument("--temperature", type=float, default=0.85)
    parser.add_argument("--beta", type=float, default=0.04)
    parser.add_argument("--reward-eval-case-limit", type=int, default=9)
    parser.add_argument("--reward-eval-max-new-tokens", type=int, default=2200)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--lora-target-modules",
        nargs="+",
        default=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    parser.add_argument("--dry-run", action="store_true", help="Write config and smoke artifacts without loading TRL.")
    return parser.parse_args()


def completion_to_text(completion: Any) -> str:
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list):
        parts: list[str] = []
        for item in completion:
            if isinstance(item, dict):
                parts.append(str(item.get("content", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if isinstance(completion, dict):
        return str(completion.get("content") or completion)
    return str(completion)


def build_dataset_rows(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in examples:
        metadata = row.get("metadata") or {}
        case_id = str(metadata.get("case_id") or "")
        prompt = str(row.get("prompt") or "")
        if not case_id or not prompt:
            continue
        rows.append(
            {
                "prompt": prompt_for_generation(prompt),
                "raw_prompt": prompt,
                "case_id": case_id,
                "task_type": metadata.get("task_type", ""),
            }
        )
    return rows


def build_grpo_config(stack: dict[str, Any], args: argparse.Namespace) -> Any:
    GRPOConfig = stack["GRPOConfig"]
    params = inspect.signature(GRPOConfig).parameters
    kwargs: dict[str, Any] = {
        "output_dir": str(args.output_dir / "checkpoints"),
        "max_steps": int(args.max_steps),
        "per_device_train_batch_size": int(args.batch_size),
        "gradient_accumulation_steps": int(args.gradient_accumulation_steps),
        "learning_rate": float(args.learning_rate),
        "logging_steps": 1,
        "save_strategy": "steps",
        "save_steps": max(10, int(args.max_steps)),
        "report_to": [],
        "remove_unused_columns": False,
        "fp16": bool(stack["torch"].cuda.is_available()),
        "bf16": False,
    }
    optional = {
        "num_generations": int(args.num_generations),
        "max_prompt_length": int(args.max_prompt_length),
        "max_completion_length": int(args.max_completion_length),
        "temperature": float(args.temperature),
        "beta": float(args.beta),
    }
    for key, value in optional.items():
        if key in params:
            kwargs[key] = value
    return GRPOConfig(**{key: value for key, value in kwargs.items() if key in params})


def load_grpo_stack() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
        from trl import GRPOConfig, GRPOTrainer
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "GRPO requires torch, datasets, peft, transformers, and trl with GRPOTrainer."
        ) from exc
    return {
        "torch": torch,
        "Dataset": Dataset,
        "LoraConfig": LoraConfig,
        "PeftModel": PeftModel,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "set_seed": set_seed,
        "GRPOConfig": GRPOConfig,
        "GRPOTrainer": GRPOTrainer,
    }


def load_policy_model(stack: dict[str, Any], args: argparse.Namespace) -> tuple[Any, Any, Any | None]:
    torch_module = stack["torch"]
    tokenizer = stack["AutoTokenizer"].from_pretrained(args.model, token=os.environ.get("HF_TOKEN") or None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch_module.float16 if torch_module.cuda.is_available() else torch_module.float32
    model = stack["AutoModelForCausalLM"].from_pretrained(
        args.model,
        torch_dtype=dtype,
        token=os.environ.get("HF_TOKEN") or None,
    )
    peft_config = None
    if not args.no_sft_adapter and args.sft_adapter_path and args.sft_adapter_path.exists():
        model = stack["PeftModel"].from_pretrained(model, str(args.sft_adapter_path), is_trainable=True)
    else:
        peft_config = stack["LoraConfig"](
            r=int(args.lora_r),
            lora_alpha=int(args.lora_alpha),
            lora_dropout=float(args.lora_dropout),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=args.lora_target_modules,
        )
    device = "cuda" if torch_module.cuda.is_available() else "cpu"
    if device != "cuda":
        model.to(device)
    return model, tokenizer, peft_config


def build_trainer(
    stack: dict[str, Any],
    model: Any,
    tokenizer: Any,
    peft_config: Any | None,
    dataset: Any,
    reward_func: Any,
    args: argparse.Namespace,
) -> Any:
    GRPOTrainer = stack["GRPOTrainer"]
    params = inspect.signature(GRPOTrainer.__init__).parameters
    kwargs: dict[str, Any] = {
        "model": model,
        "args": build_grpo_config(stack, args),
        "train_dataset": dataset,
        "reward_funcs": reward_func,
    }
    if "tokenizer" in params:
        kwargs["tokenizer"] = tokenizer
    if "processing_class" in params:
        kwargs["processing_class"] = tokenizer
    if peft_config is not None and "peft_config" in params:
        kwargs["peft_config"] = peft_config
    return GRPOTrainer(**kwargs)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(int(args.seed))
    db = load_db()
    examples = load_sft_examples(args.sft_artifact_dir)[: max(0, int(args.case_limit))]
    train_examples, eval_examples = split_examples(examples, int(args.eval_case_limit), int(args.seed))
    dataset_rows = build_dataset_rows(train_examples)
    write_jsonl(args.output_dir / "train_examples.jsonl", train_examples)
    write_jsonl(args.output_dir / "eval_examples.jsonl", eval_examples)

    config = {
        "generated_at": utc_now(),
        "model": args.model,
        "method": "GRPO environment reward",
        "sft_adapter_path": "disabled" if args.no_sft_adapter else rel_path(args.sft_adapter_path),
        "case_limit": int(args.case_limit),
        "train_case_count": len(train_examples),
        "eval_case_count": len(eval_examples),
        "max_steps": int(args.max_steps),
        "num_generations": int(args.num_generations),
        "reward_weights": DEFAULT_REWARD_WEIGHTS,
        "status": "dry_run" if args.dry_run else "started",
    }
    write_json(args.output_dir / "config.json", config)

    if args.dry_run:
        write_csv(args.output_dir / "grpo_reward_history.csv", [])
        write_csv(args.output_dir / "grpo_step_metrics.csv", [])
        write_json(args.output_dir / "final_policy_eval.json", {"status": "not_run", "reason": "dry-run"})
        print(json.dumps(to_jsonable(config), indent=2, sort_keys=True))
        return

    stack = load_grpo_stack()
    stack["set_seed"](int(args.seed))
    dataset = stack["Dataset"].from_list(dataset_rows)
    model, tokenizer, peft_config = load_policy_model(stack, args)
    reward_events: list[dict[str, Any]] = []

    def reward_func(prompts: list[Any], completions: list[Any], case_id: list[str] | None = None, **kwargs: Any) -> list[float]:
        rewards: list[float] = []
        case_ids = case_id or kwargs.get("case_id") or []
        for index, completion in enumerate(completions):
            current_case = str(case_ids[index]) if index < len(case_ids) else str(dataset_rows[index % len(dataset_rows)]["case_id"])
            text = completion_to_text(completion)
            actions, parse_success, parse_error = parse_completion(text)
            if not actions:
                actions = [sft.fallback_review_action(parse_error or "grpo_no_actions")]
            result = run_actions(
                current_case,
                actions,
                db,
                parse_success=parse_success,
                parse_error=parse_error,
            )
            reward, components = environment_reward(result, DEFAULT_REWARD_WEIGHTS)
            rewards.append(float(reward))
            reward_events.append(
                {
                    "event_index": len(reward_events) + 1,
                    "case_id": current_case,
                    "reward": reward,
                    "completion_length": len(text),
                    "parse_success": parse_success,
                    "parse_error": parse_error,
                    "score": result.get("score"),
                    "certificate_score": result.get("certificate_score"),
                    "control_satisfied_resolution": result.get("control_satisfied_resolution"),
                    "unsafe_release": result.get("unsafe_release"),
                    "reward_components": components,
                    "result_class": result.get("result_class"),
                }
            )
        return rewards

    trainer = build_trainer(stack, model, tokenizer, peft_config, dataset, reward_func, args)
    train_result = trainer.train()
    final_model_dir = args.output_dir / "final_model"
    final_model_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(args.output_dir / "tokenizer"))

    final_eval = sft.evaluate_model_policy(
        "grpo_model",
        model,
        tokenizer,
        stack["torch"],
        eval_examples[: max(0, int(args.reward_eval_case_limit))],
        db,
        max_new_tokens=int(args.reward_eval_max_new_tokens),
    )
    log_history = to_jsonable(getattr(trainer.state, "log_history", []))
    write_json(args.output_dir / "grpo_training_metrics.json", {
        "status": "completed",
        "generated_at": utc_now(),
        "train_result": to_jsonable(getattr(train_result, "metrics", {})),
        "log_history": log_history,
        "reward_event_count": len(reward_events),
    })
    write_json(args.output_dir / "final_policy_eval.json", final_eval)
    write_jsonl(args.output_dir / "per_case_results.jsonl", final_eval.get("results", []) or [])
    write_csv(args.output_dir / "grpo_reward_history.csv", reward_events)
    write_csv(args.output_dir / "grpo_step_metrics.csv", [row for row in log_history if isinstance(row, dict)])
    config["status"] = "completed"
    config["final_model_dir"] = rel_path(final_model_dir)
    config["final_policy_eval"] = rel_path(args.output_dir / "final_policy_eval.json")
    write_json(args.output_dir / "config.json", config)
    print(json.dumps(to_jsonable(final_eval.get("summary", {})), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
