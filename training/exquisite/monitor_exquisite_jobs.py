#!/usr/bin/env python3
"""Refresh Hugging Face job status for the Exquisite Training Layer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, read_json, rel_path, safe_float, utc_now, write_json
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, read_json, rel_path, safe_float, utc_now, write_json  # type: ignore


TERMINAL_STAGES = {"COMPLETED", "CANCELED", "ERROR", "DELETED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor existing Exquisite HF jobs.")
    parser.add_argument("--report-dir", type=Path, default=EXQUISITE_ROOT / "reports")
    parser.add_argument("--artifact-root", type=Path, default=EXQUISITE_ROOT)
    parser.add_argument("--refresh-artifacts", action="store_true", help="Rebuild matrix, plots, dashboard, and report after status refresh.")
    parser.add_argument("--tail-lines", type=int, default=20, help="Fetch up to this many log lines for running jobs.")
    return parser.parse_args()


def token_for_row(row: dict[str, Any]) -> str:
    if str(row.get("token_used")) == "secondary":
        return os.environ.get("HF_TOKEN_SECONDARY", "")
    return os.environ.get("HF_TOKEN_PRIMARY") or os.environ.get("HF_TOKEN", "")


def refresh_status(data: dict[str, Any], tail_lines: int) -> dict[str, Any]:
    from huggingface_hub import HfApi

    for row in data.get("jobs", []) or []:
        token = token_for_row(row)
        if not token:
            row["last_message"] = "missing_token_for_monitoring"
            continue
        api = HfApi(token=token)
        try:
            info = api.inspect_job(
                job_id=str(row.get("id") or ""),
                namespace=str(row.get("namespace_used") or ""),
                token=token,
            )
            stage = getattr(getattr(info, "status", None), "stage", None)
            row["last_status"] = getattr(stage, "value", str(stage))
            row["last_message"] = str(getattr(getattr(info, "status", None), "message", "") or "")
            if str(row.get("last_status")) == "RUNNING":
                lines: list[str] = []
                for index, line in enumerate(
                    api.fetch_job_logs(
                        job_id=str(row.get("id") or ""),
                        namespace=str(row.get("namespace_used") or ""),
                        token=token,
                    )
                ):
                    lines.append(line.rstrip())
                    if index + 1 >= max(0, int(tail_lines)):
                        break
                row["recent_log_tail"] = lines
        except Exception as exc:  # noqa: BLE001
            row["last_status"] = f"MONITOR_ERROR"
            row["last_message"] = f"{type(exc).__name__}: {exc}"
    data["generated_at"] = utc_now()
    return data


def refresh_artifacts(report_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    commands = [
        [
            "python",
            "training/exquisite/evaluate_exquisite_policy.py",
            "--artifact-root",
            "artifacts/exquisite-training",
            "--output-dir",
            "artifacts/exquisite-training/reports",
        ],
        [
            "python",
            "training/exquisite/plot_exquisite_training_results.py",
            "--artifact-root",
            "artifacts/exquisite-training",
            "--report-dir",
            "artifacts/exquisite-training/reports",
            "--output-dir",
            "artifacts/exquisite-training/plots",
        ],
        [
            "python",
            "training/exquisite/build_exquisite_dashboard.py",
            "--artifact-root",
            "artifacts/exquisite-training",
            "--report-dir",
            "artifacts/exquisite-training/reports",
            "--plot-dir",
            "artifacts/exquisite-training/plots",
            "--output-dir",
            "artifacts/exquisite-training/dashboard",
        ],
        [
            "python",
            "training/exquisite/render_exquisite_report.py",
            "--artifact-root",
            "artifacts/exquisite-training",
            "--report-dir",
            "artifacts/exquisite-training/reports",
            "--dashboard-dir",
            "artifacts/exquisite-training/dashboard",
        ],
    ]
    for command in commands:
        subprocess.run(command, cwd=repo_root, check=True)


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    jobs = [row for row in data.get("jobs", []) or [] if isinstance(row, dict) and not row.get("exclude_from_live_reports")]
    return {
        "generated_at": data.get("generated_at"),
        "job_count": len(jobs),
        "running": sum(1 for row in jobs if str(row.get("last_status")) == "RUNNING"),
        "scheduling": sum(1 for row in jobs if str(row.get("last_status")) == "SCHEDULING"),
        "completed": sum(1 for row in jobs if str(row.get("last_status")) == "COMPLETED"),
        "terminal": sum(1 for row in jobs if str(row.get("last_status")) in TERMINAL_STAGES),
        "artifact_status_file": rel_path(EXQUISITE_ROOT / "reports" / "hf_exquisite_launches.json"),
        "jobs": [
            {
                "name": row.get("name"),
                "status": row.get("last_status"),
                "message": row.get("last_message", ""),
                "url": row.get("url", ""),
            }
            for row in jobs
        ],
    }


def main() -> None:
    args = parse_args()
    status_path = args.report_dir / "hf_exquisite_launches.json"
    data = read_json(status_path, default={}) or {}
    if not data:
        raise SystemExit(f"Missing status file: {status_path}")
    data = refresh_status(data, int(args.tail_lines))
    write_json(status_path, data)
    if args.refresh_artifacts:
        refresh_artifacts(args.report_dir)
    print(json.dumps(summarize(data), indent=2))


if __name__ == "__main__":
    main()
