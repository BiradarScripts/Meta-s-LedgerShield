#!/usr/bin/env python3
"""Launch the LedgerShield Qwen TRL training job on Hugging Face A10G.

Set HF_TOKEN in the environment before running. The token is passed to the job
as a secret and is never written to the repository.
"""

from __future__ import annotations

import argparse
import os
import textwrap

from huggingface_hub import HfApi
from huggingface_hub._space_api import SpaceHardware


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch LedgerShield Qwen training on HF A10G")
    parser.add_argument("--repo-id", default="shreayas/ledgershield-controlbench")
    parser.add_argument("--namespace", default="shreayas")
    parser.add_argument("--output-dir", default="artifacts/trl-openenv-hf-a10g-qwen-rich")
    parser.add_argument("--max-steps", type=int, default=900)
    parser.add_argument("--case-limit", type=int, default=45)
    parser.add_argument("--model-eval-case-limit", type=int, default=9)
    parser.add_argument("--reward-eval-interval", type=int, default=300)
    parser.add_argument("--reward-eval-case-limit", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=3000)
    parser.add_argument("--reward-eval-max-new-tokens", type=int, default=2200)
    parser.add_argument("--seed", type=int, default=29)
    parser.add_argument("--timeout", default="8h")
    parser.add_argument("--hardware", default="A10G_LARGE", choices=["A10G_SMALL", "A10G_LARGE"])
    return parser.parse_args()


def hardware_choice(name: str) -> SpaceHardware:
    return {
        "A10G_SMALL": SpaceHardware.A10G_SMALL,
        "A10G_LARGE": SpaceHardware.A10G_LARGE,
    }[name]


def main() -> None:
    args = parse_args()
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN must be set in the environment")

    job_script = f"""
    set -euo pipefail
    export PYTHONUNBUFFERED=1
    export TOKENIZERS_PARALLELISM=false
    export LEDGERSHIELD_REMOTE_JOB=1
    export LEDGERSHIELD_HF_HARDWARE={args.hardware}
    export LEDGERSHIELD_RUN_LABEL=hf-a10g-qwen-rich
    nvidia-smi || true
    apt-get update && apt-get install -y git git-lfs
    rm -rf /workspace/ledgershield
    git clone https://huggingface.co/spaces/{args.repo_id} /workspace/ledgershield
    cd /workspace/ledgershield
    python -m pip install --upgrade pip
    python -m pip install "accelerate>=0.34,<2" "datasets>=2.20,<4" "fastapi>=0.110" "huggingface-hub>=0.36,<1.0" "httpx>=0.27" "matplotlib>=3.8" "openai>=1" "peft>=0.12,<1" "pydantic>=2" "PyYAML>=6" "requests>=2" "transformers>=4.44,<5" "trl>=0.11,<1" "uvicorn>=0.30"
    mkdir -p {args.output_dir}
    python training/ledgershield_trl_training.py \
      --output-dir {args.output_dir} \
      --case-split all \
      --case-limit {args.case_limit} \
      --train \
      --model Qwen/Qwen2.5-0.5B-Instruct \
      --max-steps {args.max_steps} \
      --batch-size {args.batch_size} \
      --gradient-accumulation-steps {args.gradient_accumulation_steps} \
      --learning-rate 2e-5 \
      --max-seq-length {args.max_seq_length} \
      --max-new-tokens {args.max_new_tokens} \
      --model-eval-case-limit {args.model_eval_case_limit} \
      --reward-eval-interval {args.reward_eval_interval} \
      --reward-eval-case-limit {args.reward_eval_case_limit} \
      --reward-eval-max-new-tokens {args.reward_eval_max_new_tokens} \
      --lora-r 16 \
      --lora-alpha 32 \
      --lora-target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
      --seed {args.seed} 2>&1 | tee {args.output_dir}/hf_job_train.log
    python - <<'UPLOAD'
    import os
    from huggingface_hub import HfApi
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.upload_folder(
        folder_path="{args.output_dir}",
        path_in_repo="{args.output_dir}",
        repo_id="{args.repo_id}",
        repo_type="space",
        token=os.environ["HF_TOKEN"],
        commit_message="Add reward-eval A10G Qwen training artifacts",
        ignore_patterns=["checkpoints/**"],
    )
    UPLOAD
    """
    api = HfApi(token=token)
    job = api.run_job(
        image="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
        command=["bash", "-lc", textwrap.dedent(job_script)],
        flavor=hardware_choice(args.hardware),
        timeout=args.timeout,
        namespace=args.namespace,
        secrets={"HF_TOKEN": token},
        token=token,
    )
    print(job.url)
    print(job.id)


if __name__ == "__main__":
    main()
