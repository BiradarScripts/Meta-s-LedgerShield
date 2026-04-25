#!/usr/bin/env python3
"""Launch LedgerShield Exquisite Training Layer jobs on Hugging Face."""

from __future__ import annotations

import argparse
import json
import os
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, extract_job_url, redact_secret, token_from_env, to_jsonable, utc_now, write_json
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, extract_job_url, redact_secret, token_from_env, to_jsonable, utc_now, write_json  # type: ignore


@dataclass(frozen=True)
class RunSpec:
    name: str
    hardware: str
    command: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Exquisite HF Jobs.")
    parser.add_argument("--repo-id", default="shreayas/ledgershield-controlbench")
    parser.add_argument("--namespace", default="shreayas")
    parser.add_argument("--timeout", default="8h")
    parser.add_argument("--runs", nargs="*", default=["selfplay-0.5b", "grpo-0.5b", "sft-1.5b", "grpo-1.5b", "grpo-3b-flagship", "dpo-falsifier-distill"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=90)
    parser.add_argument("--image", default="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel")
    return parser.parse_args()


def postprocess_command() -> str:
    return " && ".join(
        [
            "python training/exquisite/evaluate_exquisite_policy.py --artifact-root artifacts/exquisite-training --output-dir artifacts/exquisite-training/reports",
            "python training/exquisite/plot_exquisite_training_results.py --artifact-root artifacts/exquisite-training --report-dir artifacts/exquisite-training/reports --output-dir artifacts/exquisite-training/plots",
            "python training/exquisite/build_exquisite_dashboard.py --artifact-root artifacts/exquisite-training --report-dir artifacts/exquisite-training/reports --plot-dir artifacts/exquisite-training/plots --output-dir artifacts/exquisite-training/dashboard",
        ]
    )


def upload_command(repo_id: str) -> str:
    return textwrap.dedent(
        f"""
        python - <<'UPLOAD'
        import os
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ["HF_TOKEN"])
        api.upload_folder(
            folder_path="artifacts/exquisite-training",
            path_in_repo="artifacts/exquisite-training",
            repo_id="{repo_id}",
            repo_type="space",
            token=os.environ["HF_TOKEN"],
            commit_message="Add Exquisite Training Layer artifacts",
            ignore_patterns=["**/checkpoints/**", "**/__pycache__/**"],
        )
        UPLOAD
        """
    ).strip()


def base_job_preamble(repo_id: str) -> str:
    return textwrap.dedent(
        f"""
        set -euo pipefail
        export PYTHONUNBUFFERED=1
        export TOKENIZERS_PARALLELISM=false
        export LEDGERSHIELD_REMOTE_JOB=1
        nvidia-smi || true
        apt-get update && apt-get install -y git git-lfs
        rm -rf /workspace/ledgershield
        git clone https://huggingface.co/spaces/{repo_id} /workspace/ledgershield
        cd /workspace/ledgershield
        python -m pip install --upgrade pip
        python -m pip install -r training/requirements-training.txt
        mkdir -p artifacts/exquisite-training/reports
        """
    ).strip()


def run_specs(repo_id: str) -> dict[str, RunSpec]:
    post = postprocess_command()
    upload = upload_command(repo_id)
    sft_1_5_cmd = " ".join(
        [
            "python training/ledgershield_trl_training.py",
            "--output-dir artifacts/exquisite-training/sft-1.5b",
            "--case-split all --case-limit 45 --train",
            "--model Qwen/Qwen2.5-1.5B-Instruct",
            "--max-steps 900 --batch-size 1 --gradient-accumulation-steps 4",
            "--learning-rate 2e-5 --max-seq-length 4096 --max-new-tokens 3000",
            "--model-eval-case-limit 9 --reward-eval-interval 300 --reward-eval-case-limit 3",
            "--reward-eval-max-new-tokens 2200 --lora-r 16 --lora-alpha 32",
            "--lora-target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj --seed 41",
        ]
    )
    warm_sft_1_5_cmd = sft_1_5_cmd.replace("artifacts/exquisite-training/sft-1.5b", "artifacts/exquisite-training/sft-1.5b-warmstart")
    warm_sft_3b_cmd = sft_1_5_cmd.replace("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-3B-Instruct").replace("artifacts/exquisite-training/sft-1.5b", "artifacts/exquisite-training/sft-3b-warmstart").replace("--max-steps 900", "--max-steps 600")
    specs = {
        "selfplay-0.5b": RunSpec(
            name="selfplay-0.5b",
            hardware="a100-large",
            description="Collect SFT-warm-start self-play candidates and falsifier preferences.",
            command=" && ".join(
                [
                    "python training/exquisite/collect_selfplay_rollouts.py --output-dir artifacts/exquisite-training/selfplay-0.5b --mode model --model Qwen/Qwen2.5-0.5B-Instruct --adapter-path artifacts/trl-openenv-hf-a10g-qwen-rich/final_model --case-limit 45 --eval-case-limit 9 --num-generations 8 --max-new-tokens 2600 --seed 29",
                    post,
                    upload,
                ]
            ),
        ),
        "grpo-0.5b": RunSpec(
            name="grpo-0.5b",
            hardware="a100-large",
            description="Run GRPO from the existing 0.5B SFT adapter.",
            command=" && ".join(
                [
                    "python training/exquisite/grpo_env_reward_training.py --output-dir artifacts/exquisite-training/grpo-0.5b --model Qwen/Qwen2.5-0.5B-Instruct --sft-adapter-path artifacts/trl-openenv-hf-a10g-qwen-rich/final_model --case-limit 45 --eval-case-limit 9 --max-steps 250 --num-generations 4 --max-completion-length 1800 --seed 31",
                    post,
                    upload,
                ]
            ),
        ),
        "sft-1.5b": RunSpec(
            name="sft-1.5b",
            hardware="a100-large",
            description="Run larger-model SFT to show model scaling.",
            command=" && ".join([sft_1_5_cmd, post, upload]),
        ),
        "grpo-1.5b": RunSpec(
            name="grpo-1.5b",
            hardware="a100-large",
            description="Run 1.5B SFT warm start followed by GRPO.",
            command=" && ".join(
                [
                    warm_sft_1_5_cmd,
                    "python training/exquisite/grpo_env_reward_training.py --output-dir artifacts/exquisite-training/grpo-1.5b --model Qwen/Qwen2.5-1.5B-Instruct --sft-adapter-path artifacts/exquisite-training/sft-1.5b-warmstart/final_model --case-limit 45 --eval-case-limit 9 --max-steps 250 --num-generations 4 --max-completion-length 1800 --seed 43",
                    post,
                    upload,
                ]
            ),
        ),
        "grpo-3b-flagship": RunSpec(
            name="grpo-3b-flagship",
            hardware="a100-large",
            description="Run 3B flagship SFT warm start followed by GRPO.",
            command=" && ".join(
                [
                    warm_sft_3b_cmd,
                    "python training/exquisite/grpo_env_reward_training.py --output-dir artifacts/exquisite-training/grpo-3b-flagship --model Qwen/Qwen2.5-3B-Instruct --sft-adapter-path artifacts/exquisite-training/sft-3b-warmstart/final_model --case-limit 45 --eval-case-limit 9 --max-steps 220 --num-generations 4 --max-completion-length 1800 --seed 53",
                    post,
                    upload,
                ]
            ),
        ),
        "dpo-falsifier-distill": RunSpec(
            name="dpo-falsifier-distill",
            hardware="a100-large",
            description="Build preference pairs if needed and run DPO distillation.",
            command=" && ".join(
                [
                    "test -s artifacts/exquisite-training/selfplay-0.5b/falsifier_preferences.jsonl || python training/exquisite/collect_selfplay_rollouts.py --output-dir artifacts/exquisite-training/selfplay-0.5b --mode model --model Qwen/Qwen2.5-0.5B-Instruct --adapter-path artifacts/trl-openenv-hf-a10g-qwen-rich/final_model --case-limit 45 --eval-case-limit 9 --num-generations 8 --max-new-tokens 2600 --seed 29",
                    "python training/exquisite/dpo_falsifier_distill.py --output-dir artifacts/exquisite-training/dpo-falsifier-distill --preference-file artifacts/exquisite-training/selfplay-0.5b/falsifier_preferences.jsonl --model Qwen/Qwen2.5-0.5B-Instruct --adapter-path artifacts/trl-openenv-hf-a10g-qwen-rich/final_model --max-steps 180 --seed 37",
                    post,
                    upload,
                ]
            ),
        ),
    }
    return specs


def launch_job(api: Any, token: str, args: argparse.Namespace, spec: RunSpec) -> Any:
    command = f"{base_job_preamble(args.repo_id)}\n{spec.command}"
    return api.run_job(
        image=args.image,
        command=["bash", "-lc", command],
        flavor=spec.hardware,
        timeout=args.timeout,
        namespace=args.namespace,
        secrets={"HF_TOKEN": token},
        token=token,
    )


def should_fallback(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(fragment in text for fragment in ["credit", "quota", "payment", "billing", "insufficient", "limit"])


def monitor_jobs(api: Any, jobs: list[dict[str, Any]], poll_seconds: int) -> None:
    if not jobs:
        return
    print(f"[monitor] tracking {len(jobs)} jobs")
    while True:
        unfinished = 0
        for record in jobs:
            job_id = record.get("id")
            if not job_id:
                continue
            status = "unknown"
            try:
                if hasattr(api, "get_job"):
                    info = api.get_job(job_id)
                elif hasattr(api, "job_info"):
                    info = api.job_info(job_id)
                else:
                    info = None
                status = str(getattr(info, "status", "unknown") if info is not None else "unknown")
            except Exception as exc:  # noqa: BLE001
                status = f"monitor_error:{exc}"
            record["last_status"] = status
            if not any(done in status.lower() for done in ["done", "success", "failed", "error", "cancel"]):
                unfinished += 1
            print(f"[monitor] {record.get('name')} {job_id} {status}", flush=True)
        write_json(EXQUISITE_ROOT / "reports" / "hf_exquisite_launches.json", {"generated_at": utc_now(), "jobs": jobs})
        if unfinished == 0:
            break
        time.sleep(max(15, int(poll_seconds)))


def main() -> None:
    args = parse_args()
    specs = run_specs(args.repo_id)
    selected = [specs[name] for name in args.runs if name in specs]
    unknown = [name for name in args.runs if name not in specs]
    if unknown:
        raise SystemExit(f"Unknown run names: {', '.join(unknown)}")
    launch_records: list[dict[str, Any]] = []
    if args.dry_run:
        for spec in selected:
            launch_records.append({"name": spec.name, "hardware": spec.hardware, "description": spec.description, "command": spec.command})
        write_json(EXQUISITE_ROOT / "reports" / "hf_exquisite_launches.json", {"generated_at": utc_now(), "dry_run": True, "jobs": launch_records})
        print(json.dumps(to_jsonable({"dry_run": True, "runs": launch_records}), indent=2, sort_keys=True))
        return

    primary = token_from_env(primary=True)
    secondary = token_from_env(primary=False)
    if not primary:
        raise SystemExit("Set HF_TOKEN_PRIMARY or HF_TOKEN in the environment before launching. Set HF_TOKEN_SECONDARY for account fallback.")
    from huggingface_hub import HfApi

    active_api = HfApi(token=primary)
    for spec in selected:
        token_used = "primary"
        try:
            job = launch_job(active_api, primary, args, spec)
        except Exception as exc:  # noqa: BLE001
            if secondary and should_fallback(exc):
                token_used = "secondary"
                active_api = HfApi(token=secondary)
                job = launch_job(active_api, secondary, args, spec)
            else:
                raise
        record = {
            "name": spec.name,
            "description": spec.description,
            "hardware": spec.hardware,
            "token_used": token_used,
            "token_redacted": redact_secret(primary if token_used == "primary" else secondary),
            "url": extract_job_url(job),
            "id": str(getattr(job, "id", "")),
            "launched_at": utc_now(),
        }
        launch_records.append(record)
        write_json(EXQUISITE_ROOT / "reports" / "hf_exquisite_launches.json", {"generated_at": utc_now(), "jobs": launch_records})
        print(json.dumps(to_jsonable(record), indent=2, sort_keys=True), flush=True)
    if args.monitor:
        monitor_jobs(active_api, launch_records, int(args.poll_seconds))


if __name__ == "__main__":
    main()
