#!/usr/bin/env python3
"""Launch LedgerShield Exquisite Training Layer jobs on Hugging Face."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import textwrap
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, extract_job_url, read_json, redact_secret, token_from_env, to_jsonable, utc_now, write_json
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, extract_job_url, read_json, redact_secret, token_from_env, to_jsonable, utc_now, write_json  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_FOLDERS = ["server", "training", "docs"]
SYNC_FILES = [
    "__init__.py",
    "README.md",
    "Dockerfile",
    "benchmark_report.py",
    "client.py",
    "inference.py",
    "ledgershield_env.py",
    "llm_utils.py",
    "models.py",
    "openenv.yaml",
    "openenv_compat.py",
    "pyproject.toml",
    "requirements.txt",
    "task_c_guardrails.py",
    "task_d_guardrails.py",
    "uv.lock",
    "validate-submission.sh",
]
SYNC_IGNORE_PATTERNS = [
    "**/.DS_Store",
    "**/.git/**",
    "**/.next/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/node_modules/**",
]
HARDWARE_COST_PER_HOUR = {
    "a10g-large": 1.50,
    "a100-large": 2.50,
    "a100x4": 10.00,
    "a100x8": 20.00,
    "h200": 5.00,
}
HARDWARE_GPU_COUNT = {
    "a10g-large": 1,
    "a100-large": 1,
    "a100x4": 4,
    "a100x8": 8,
    "h200": 1,
}


@dataclass(frozen=True)
class RunSpec:
    name: str
    hardware: str
    timeout: str
    command: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Exquisite HF Jobs.")
    parser.add_argument("--repo-id", default="shreayas/ledgershield-controlbench")
    parser.add_argument("--namespace", default="shreayas")
    parser.add_argument("--timeout", default="", help="Optional global timeout override for every selected run.")
    parser.add_argument("--runs", nargs="*", default=["selfplay-0.5b", "grpo-0.5b", "sft-1.5b", "grpo-1.5b", "grpo-3b-flagship", "dpo-falsifier-distill"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=90)
    parser.add_argument("--image", default="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel")
    parser.add_argument("--skip-source-sync", action="store_true", help="Do not upload local source files into the Space repo before launching jobs.")
    return parser.parse_args()


def postprocess_command() -> str:
    return " && ".join(
        [
            "python training/exquisite/evaluate_exquisite_policy.py --artifact-root artifacts/exquisite-training --output-dir artifacts/exquisite-training/reports",
            "python training/exquisite/plot_exquisite_training_results.py --artifact-root artifacts/exquisite-training --report-dir artifacts/exquisite-training/reports --output-dir artifacts/exquisite-training/plots",
            "python training/exquisite/build_exquisite_dashboard.py --artifact-root artifacts/exquisite-training --report-dir artifacts/exquisite-training/reports --plot-dir artifacts/exquisite-training/plots --output-dir artifacts/exquisite-training/dashboard",
            "python training/exquisite/render_exquisite_report.py --artifact-root artifacts/exquisite-training --report-dir artifacts/exquisite-training/reports --dashboard-dir artifacts/exquisite-training/dashboard",
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


def parse_timeout_hours(value: str) -> float:
    text = str(value).strip().lower()
    if not text:
        return 0.0
    if text.endswith("ms"):
        return float(text[:-2]) / 3_600_000.0
    if text.endswith("s"):
        return float(text[:-1]) / 3600.0
    if text.endswith("m"):
        return float(text[:-1]) / 60.0
    if text.endswith("h"):
        return float(text[:-1])
    return float(text)


def launched_elapsed_hours(timestamp: str) -> float:
    try:
        started = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc) - started).total_seconds() / 3600.0)


def sync_local_source(api: Any, token: str, repo_id: str) -> dict[str, Any]:
    commit_message = f"Sync Exquisite training source ({utc_now()})"
    uploaded_folders: list[str] = []
    uploaded_files: list[str] = []
    for folder in SYNC_FOLDERS:
        path = REPO_ROOT / folder
        if not path.exists():
            continue
        api.upload_folder(
            folder_path=str(path),
            path_in_repo=folder,
            repo_id=repo_id,
            repo_type="space",
            token=token,
            commit_message=commit_message,
            ignore_patterns=SYNC_IGNORE_PATTERNS,
        )
        uploaded_folders.append(folder)
    for relative in SYNC_FILES:
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=relative,
            repo_id=repo_id,
            repo_type="space",
            token=token,
            commit_message=commit_message,
        )
        uploaded_files.append(relative)
    return {
        "synced_at": utc_now(),
        "repo_id": repo_id,
        "folders": uploaded_folders,
        "files": uploaded_files,
        "source_branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True
        ).strip(),
    }


def run_specs(repo_id: str) -> dict[str, RunSpec]:
    post = postprocess_command()
    upload = upload_command(repo_id)
    sft_1_5_cmd = " ".join(
        [
            "python training/ledgershield_trl_training.py",
            "--output-dir artifacts/exquisite-training/sft-1.5b",
            "--case-split all --case-limit 45 --train",
            "--model Qwen/Qwen2.5-1.5B-Instruct",
            "--max-steps 300 --batch-size 1 --gradient-accumulation-steps 4",
            "--learning-rate 2e-5 --max-seq-length 4096 --max-new-tokens 1200",
            "--model-eval-case-limit 3 --skip-base-model-eval --reward-eval-interval 0 --reward-eval-case-limit 0",
            "--reward-eval-max-new-tokens 0 --lora-r 16 --lora-alpha 32",
            "--lora-target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj --seed 41 --no-plots",
        ]
    )
    warm_sft_1_5_cmd = sft_1_5_cmd.replace("artifacts/exquisite-training/sft-1.5b", "artifacts/exquisite-training/sft-1.5b-warmstart")
    warm_sft_3b_cmd = sft_1_5_cmd.replace("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-3B-Instruct").replace("artifacts/exquisite-training/sft-1.5b", "artifacts/exquisite-training/sft-3b-warmstart").replace("--max-steps 300", "--max-steps 400")
    specs = {
        "selfplay-0.5b": RunSpec(
            name="selfplay-0.5b",
            hardware="a10g-large",
            timeout="2h",
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
            timeout="4h",
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
            timeout="3h",
            description="Run a fast 1.5B SFT profile for model-scaling evidence within budget.",
            command=" && ".join([sft_1_5_cmd, post, upload]),
        ),
        "grpo-1.5b": RunSpec(
            name="grpo-1.5b",
            hardware="a100-large",
            timeout="5h",
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
            timeout="5h",
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
            hardware="a10g-large",
            timeout="3h",
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


def timeout_for_run(args: argparse.Namespace, spec: RunSpec) -> str:
    return str(args.timeout).strip() or spec.timeout


def account_name(token: str) -> str:
    from huggingface_hub import HfApi

    info = HfApi(token=token).whoami(token=token)
    return str(info.get("name") or "").strip()


def launch_job(
    api: Any,
    auth_token: str,
    upload_token: str,
    namespace: str,
    args: argparse.Namespace,
    spec: RunSpec,
) -> Any:
    command = f"{base_job_preamble(args.repo_id)}\n{spec.command}"
    timeout = timeout_for_run(args, spec)
    return api.run_job(
        image=args.image,
        command=["bash", "-lc", command],
        flavor=spec.hardware,
        timeout=timeout,
        namespace=namespace,
        secrets={"HF_TOKEN": upload_token},
        token=auth_token,
    )


def should_fallback(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(fragment in text for fragment in ["credit", "quota", "payment", "billing", "insufficient", "limit"])


def terminal_stage(stage: str) -> bool:
    return stage.upper() in {"COMPLETED", "CANCELED", "ERROR", "DELETED"}


def status_file_path() -> Path:
    return EXQUISITE_ROOT / "reports" / "hf_exquisite_launches.json"


def monitor_jobs(primary_token: str, secondary_token: str, jobs: list[dict[str, Any]], poll_seconds: int) -> None:
    from huggingface_hub import HfApi

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
            message = ""
            try:
                token = primary_token if record.get("token_used") != "secondary" else secondary_token
                api = HfApi(token=token)
                info = api.inspect_job(
                    job_id=job_id,
                    namespace=str(record.get("namespace_used") or ""),
                    token=token,
                )
                stage = getattr(getattr(info, "status", None), "stage", None)
                status = str(getattr(stage, "value", stage) or "unknown")
                message = str(getattr(getattr(info, "status", None), "message", "") or "")
            except Exception as exc:  # noqa: BLE001
                status = f"monitor_error:{exc}"
                message = str(exc)
            record["last_status"] = status
            record["last_message"] = message
            record["elapsed_hours"] = round(launched_elapsed_hours(str(record.get("launched_at") or "")), 3)
            if not terminal_stage(status):
                unfinished += 1
            print(f"[monitor] {record.get('name')} {job_id} {status} {message}".strip(), flush=True)
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
    status_path = status_file_path()
    existing_payload = read_json(status_path, default={}) or {}
    existing_jobs = existing_payload.get("jobs", []) if isinstance(existing_payload, dict) else []
    launch_records: list[dict[str, Any]] = [dict(row) for row in existing_jobs if isinstance(row, dict)]
    existing_source_sync = (
        existing_payload.get("source_sync") if isinstance(existing_payload, dict) and isinstance(existing_payload.get("source_sync"), dict) else None
    )
    if args.dry_run:
        preview_records: list[dict[str, Any]] = []
        for spec in selected:
            preview_records.append(
                {
                    "name": spec.name,
                    "hardware": spec.hardware,
                    "description": spec.description,
                    "command": spec.command,
                    "gpu_count": HARDWARE_GPU_COUNT.get(spec.hardware, 1),
                    "hourly_cost_usd": HARDWARE_COST_PER_HOUR.get(spec.hardware),
                    "timeout": timeout_for_run(args, spec),
                    "timeout_hours": round(parse_timeout_hours(timeout_for_run(args, spec)), 3),
                    "max_cost_usd": round(parse_timeout_hours(timeout_for_run(args, spec)) * HARDWARE_COST_PER_HOUR.get(spec.hardware, 0.0), 2),
                    "last_status": "DRY_RUN",
                    "url": "",
                }
            )
        write_json(status_path, {"generated_at": utc_now(), "dry_run": True, "source_sync": existing_source_sync, "jobs": launch_records, "preview_runs": preview_records})
        print(json.dumps(to_jsonable({"dry_run": True, "runs": preview_records}), indent=2, sort_keys=True))
        return

    primary = token_from_env(primary=True)
    secondary = token_from_env(primary=False)
    if not primary:
        raise SystemExit("Set HF_TOKEN_PRIMARY or HF_TOKEN in the environment before launching. Set HF_TOKEN_SECONDARY for account fallback.")
    from huggingface_hub import HfApi

    primary_namespace = args.namespace or account_name(primary)
    secondary_namespace = account_name(secondary) if secondary else ""
    active_api = HfApi(token=primary)
    active_token = primary
    source_sync: dict[str, Any] | None = existing_source_sync
    if not args.skip_source_sync:
        source_sync = sync_local_source(active_api, primary, args.repo_id)
        write_json(
            status_path,
            {"generated_at": utc_now(), "source_sync": source_sync, "jobs": launch_records},
        )
    selected_names = {spec.name for spec in selected}
    for row in launch_records:
        if str(row.get("name") or "") in selected_names and not row.get("exclude_from_live_reports"):
            row["exclude_from_live_reports"] = True
            row["status_reason"] = "superseded_relaunch"
            row["superseded_at"] = utc_now()
    for spec in selected:
        token_used = "primary"
        namespace_used = primary_namespace
        try:
            job = launch_job(active_api, primary, primary, primary_namespace, args, spec)
        except Exception as exc:  # noqa: BLE001
            if secondary and should_fallback(exc):
                token_used = "secondary"
                namespace_used = secondary_namespace or primary_namespace
                active_api = HfApi(token=secondary)
                active_token = secondary
                job = launch_job(active_api, secondary, primary, namespace_used, args, spec)
            else:
                raise
        record = {
            "name": spec.name,
            "description": spec.description,
            "hardware": spec.hardware,
            "gpu_count": HARDWARE_GPU_COUNT.get(spec.hardware, 1),
            "hourly_cost_usd": HARDWARE_COST_PER_HOUR.get(spec.hardware),
            "timeout": timeout_for_run(args, spec),
            "timeout_hours": round(parse_timeout_hours(timeout_for_run(args, spec)), 3),
            "max_cost_usd": round(parse_timeout_hours(timeout_for_run(args, spec)) * HARDWARE_COST_PER_HOUR.get(spec.hardware, 0.0), 2),
            "token_used": token_used,
            "namespace_used": namespace_used,
            "token_redacted": redact_secret(primary if token_used == "primary" else secondary),
            "url": extract_job_url(job),
            "id": str(getattr(job, "id", "")),
            "launched_at": utc_now(),
            "last_status": str(getattr(getattr(getattr(job, "status", None), "stage", None), "value", "") or ""),
        }
        launch_records.append(record)
        write_json(
            status_path,
            {"generated_at": utc_now(), "source_sync": source_sync, "jobs": launch_records},
        )
        print(json.dumps(to_jsonable(record), indent=2, sort_keys=True), flush=True)
    if args.monitor:
        monitor_jobs(primary, secondary, launch_records, int(args.poll_seconds))


if __name__ == "__main__":
    main()
