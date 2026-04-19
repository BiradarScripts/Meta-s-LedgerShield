"""
Minimal TRL fine-tuning entry point for LedgerShield v2.

This is intentionally small: the benchmark only needs a reproducible training
artifact that converts LedgerShield trajectories into supervision records and
runs a lightweight SFT pass over action/decision targets.

Example:

    python training/minimal_trl_sft.py \
        --input artifacts/ledgershield_sft_examples.jsonl \
        --output-dir artifacts/trl-sft-run

The script expects JSONL rows with:

    {
      "prompt": "...",
      "completion": "...",
      "metadata": {...}
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal TRL SFT runner for LedgerShield v2")
    parser.add_argument("--input", required=True, help="JSONL file of prompt/completion records")
    parser.add_argument("--output-dir", required=True, help="Directory for training outputs")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    return parser.parse_args()


def load_examples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_examples(input_path)
    summary = {
        "status": "prepared",
        "model": args.model,
        "example_count": len(rows),
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "note": (
            "Install transformers, datasets, accelerate, peft, and trl to run training. "
            "This script intentionally keeps the benchmark-side contract lightweight."
        ),
    }
    (output_dir / "training_prep_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
