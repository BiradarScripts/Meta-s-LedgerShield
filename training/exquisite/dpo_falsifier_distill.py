#!/usr/bin/env python3
"""Distill falsifier-scored self-play preferences with DPO."""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import (
        EXISTING_SFT_DIR,
        EXQUISITE_ROOT,
        load_db,
        load_sft_examples,
        read_jsonl,
        rel_path,
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
        EXISTING_SFT_DIR,
        EXQUISITE_ROOT,
        load_db,
        load_sft_examples,
        read_jsonl,
        rel_path,
        split_examples,
        sft,
        to_jsonable,
        utc_now,
        write_csv,
        write_json,
        write_jsonl,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DPO distillation from LedgerShield falsifier preferences.")
    parser.add_argument("--output-dir", type=Path, default=EXQUISITE_ROOT / "dpo-falsifier-distill")
    parser.add_argument("--preference-file", type=Path, default=EXQUISITE_ROOT / "selfplay-0.5b" / "falsifier_preferences.jsonl")
    parser.add_argument("--sft-artifact-dir", type=Path, default=EXISTING_SFT_DIR)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--adapter-path", type=Path, default=EXISTING_SFT_DIR / "final_model")
    parser.add_argument("--case-limit", type=int, default=45)
    parser.add_argument("--eval-case-limit", type=int, default=9)
    parser.add_argument("--max-steps", type=int, default=180)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--beta", type=float, default=0.10)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--eval-max-new-tokens", type=int, default=2200)
    parser.add_argument("--seed", type=int, default=37)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_dpo_stack() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
        from trl import DPOConfig, DPOTrainer
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("DPO requires torch, datasets, peft, transformers, and trl.") from exc
    return {
        "torch": torch,
        "Dataset": Dataset,
        "PeftModel": PeftModel,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "set_seed": set_seed,
        "DPOConfig": DPOConfig,
        "DPOTrainer": DPOTrainer,
    }


def build_dpo_config(stack: dict[str, Any], args: argparse.Namespace) -> Any:
    DPOConfig = stack["DPOConfig"]
    params = inspect.signature(DPOConfig).parameters
    kwargs = {
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
        "beta": float(args.beta),
        "max_length": int(args.max_length),
    }
    return DPOConfig(**{key: value for key, value in kwargs.items() if key in params})


def load_model(stack: dict[str, Any], args: argparse.Namespace) -> tuple[Any, Any]:
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
    if args.adapter_path and args.adapter_path.exists():
        model = stack["PeftModel"].from_pretrained(model, str(args.adapter_path), is_trainable=True)
    if not torch_module.cuda.is_available():
        model.to("cpu")
    return model, tokenizer


def normalize_pairs(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    for row in rows:
        prompt = str(row.get("prompt") or "")
        chosen = str(row.get("chosen") or "")
        rejected = str(row.get("rejected") or "")
        if prompt and chosen and rejected and chosen != rejected:
            pairs.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
    return pairs


def build_trainer(stack: dict[str, Any], model: Any, tokenizer: Any, dataset: Any, args: argparse.Namespace) -> Any:
    DPOTrainer = stack["DPOTrainer"]
    params = inspect.signature(DPOTrainer.__init__).parameters
    kwargs: dict[str, Any] = {
        "model": model,
        "args": build_dpo_config(stack, args),
        "train_dataset": dataset,
    }
    if "ref_model" in params:
        kwargs["ref_model"] = None
    if "tokenizer" in params:
        kwargs["tokenizer"] = tokenizer
    if "processing_class" in params:
        kwargs["processing_class"] = tokenizer
    return DPOTrainer(**kwargs)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_pairs = read_jsonl(args.preference_file)
    pairs = normalize_pairs(raw_pairs)
    write_jsonl(args.output_dir / "falsifier_preferences.jsonl", raw_pairs)
    write_jsonl(args.output_dir / "dpo_pairs.jsonl", pairs)
    config = {
        "generated_at": utc_now(),
        "method": "DPO falsifier preference distillation",
        "model": args.model,
        "adapter_path": rel_path(args.adapter_path),
        "preference_file": rel_path(args.preference_file),
        "preference_pair_count": len(pairs),
        "max_steps": int(args.max_steps),
        "status": "dry_run" if args.dry_run else "started",
    }
    write_json(args.output_dir / "config.json", config)
    if args.dry_run or not pairs:
        reason = "dry-run" if args.dry_run else "no preference pairs found"
        write_csv(args.output_dir / "dpo_step_metrics.csv", [])
        write_json(args.output_dir / "final_policy_eval.json", {"status": "not_run", "reason": reason})
        print(json.dumps(to_jsonable({**config, "reason": reason}), indent=2, sort_keys=True))
        return

    db = load_db()
    examples = load_sft_examples(args.sft_artifact_dir)[: max(0, int(args.case_limit))]
    _, eval_examples = split_examples(examples, int(args.eval_case_limit), int(args.seed))
    stack = load_dpo_stack()
    stack["set_seed"](int(args.seed))
    dataset = stack["Dataset"].from_list(pairs)
    model, tokenizer = load_model(stack, args)
    trainer = build_trainer(stack, model, tokenizer, dataset, args)
    train_result = trainer.train()
    final_model_dir = args.output_dir / "final_model"
    final_model_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(args.output_dir / "tokenizer"))
    final_eval = sft.evaluate_model_policy(
        "dpo_falsifier_model",
        model,
        tokenizer,
        stack["torch"],
        eval_examples,
        db,
        max_new_tokens=int(args.eval_max_new_tokens),
    )
    log_history = to_jsonable(getattr(trainer.state, "log_history", []))
    write_json(args.output_dir / "dpo_training_metrics.json", {
        "status": "completed",
        "generated_at": utc_now(),
        "train_result": to_jsonable(getattr(train_result, "metrics", {})),
        "log_history": log_history,
    })
    write_csv(args.output_dir / "dpo_step_metrics.csv", [row for row in log_history if isinstance(row, dict)])
    write_json(args.output_dir / "final_policy_eval.json", final_eval)
    write_jsonl(args.output_dir / "per_case_results.jsonl", final_eval.get("results", []) or [])
    config["status"] = "completed"
    config["final_model_dir"] = rel_path(final_model_dir)
    write_json(args.output_dir / "config.json", config)
    print(json.dumps(to_jsonable(final_eval.get("summary", {})), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
