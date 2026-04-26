#!/usr/bin/env python3
"""Render a consistent Exquisite Training report from current artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, maybe_float, public_launch_row, read_csv, read_json, rel_path, safe_float, utc_now
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, maybe_float, public_launch_row, read_csv, read_json, rel_path, safe_float, utc_now  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Exquisite artifact report.")
    parser.add_argument("--artifact-root", type=Path, default=EXQUISITE_ROOT)
    parser.add_argument("--report-dir", type=Path, default=EXQUISITE_ROOT / "reports")
    parser.add_argument("--dashboard-dir", type=Path, default=EXQUISITE_ROOT / "dashboard")
    return parser.parse_args()


def load_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    matrix = read_csv(args.report_dir / "final_policy_matrix.csv")
    summary = read_json(args.report_dir / "exquisite_training_summary.json", default={}) or {}
    manifest = read_json(args.report_dir / "visualization_manifest.json", default={}) or {}
    launches = read_json(args.report_dir / "hf_exquisite_launches.json", default={}) or {}
    return matrix, summary, manifest, launches


def best_numeric_row(matrix: list[dict[str, Any]]) -> dict[str, Any] | None:
    numeric = []
    for row in matrix:
        score = maybe_float(row.get("mean_score"))
        if score is not None:
            numeric.append((score, row))
    if not numeric:
        return None
    return max(numeric, key=lambda pair: pair[0])[1]


def policy_label(row: dict[str, Any]) -> str:
    model = str(row.get("model") or "")
    policy = str(row.get("policy") or "")
    if model and model != "-" and model not in policy:
        return f"{policy} {model}"
    return policy


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join(["---"] * len(columns)) + "|"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, divider, *body])


def render_report(args: argparse.Namespace) -> str:
    matrix, summary, manifest, launches = load_rows(args)
    best = best_numeric_row(matrix) or {}
    jobs = launches.get("jobs", []) if isinstance(launches, dict) else []
    jobs = [public_launch_row(row) for row in jobs if isinstance(row, dict) and not row.get("exclude_from_live_reports")]
    source_sync = launches.get("source_sync", {}) if isinstance(launches, dict) else {}
    excluded_runs = summary.get("excluded_runs", []) if isinstance(summary, dict) else []
    plot_count = int(safe_float((manifest if isinstance(manifest, dict) else {}).get("plot_count")))
    completed_jobs = sum(1 for row in jobs if str(row.get("public_status", "")).upper() == "COMPLETE")
    running_jobs = sum(1 for row in jobs if str(row.get("public_status", "")).upper() == "RUNNING")
    planned_gpu_hours = sum(safe_float(row.get("timeout_hours")) * safe_float(row.get("gpu_count"), 1.0) for row in jobs)
    planned_cost = sum(safe_float(row.get("max_cost_usd")) for row in jobs)

    key_paths = [
        ("Exquisite docs", "docs/DOCUMENTATION.md#exquisite-training-layer"),
        ("Visual analysis docs", "docs/DOCUMENTATION.md#exquisite-visual-analysis"),
        ("Training package", "training/exquisite/"),
        ("Policy matrix", rel_path(args.report_dir / "final_policy_matrix.csv")),
        ("Visualization manifest", rel_path(args.report_dir / "visualization_manifest.json")),
        ("Dashboard", rel_path(args.dashboard_dir / "index.html")),
    ]
    launch_columns = ["name", "hardware", "public_status", "public_note", "timeout", "hourly_cost_usd", "max_cost_usd"]
    policy_columns = ["policy", "model", "method", "mean_score", "certificate_score", "control_satisfied", "unsafe_release", "parse_success", "status"]
    numeric_matrix = [row for row in matrix if maybe_float(row.get("mean_score")) is not None or row.get("status") == "PENDING"]

    text = f"""# LedgerShield Exquisite Training Report

Generated at `{utc_now()}`.

## Summary

LedgerShield now has two stacked training layers:

- Existing SFT proof: live OpenEnv rollouts, Qwen 0.5B LoRA, A10G TRL run, held-out score improvement from `0.1283` to `0.4394`, and zero unsafe release.
- Exquisite layer: self-play candidate generation, LedgerShield environment execution, deterministic falsifier reward, GRPO online RL, optional DPO preference distillation, scaling-law analysis, and a 56-plot visualization pack.

The current best numeric policy is `{policy_label(best) if best else "PENDING"}` with mean score `{best.get("mean_score", "PENDING") if best else "PENDING"}`.

## Status

- Policy rows completed: `{summary.get("completed_policy_count", 0)}` of `{summary.get("policy_count", 0)}`
- New-policy rows pending artifact sync: `{summary.get("pending_policy_count", 0)}`
- Self-play candidates recorded: `{summary.get("selfplay_candidate_count", 0)}`
- Plots generated: `{plot_count}`
- Live runs still active: `{running_jobs}`
- Artifact-complete runs: `{completed_jobs}`
- Planned GPU hours: `{planned_gpu_hours:.1f}`
- Planned max cost (based on timeout caps): `${planned_cost:.2f}`
- Live report exclusions: `{", ".join(excluded_runs) if excluded_runs else "none"}`

## Source Sync

- Synced at: `{source_sync.get("synced_at", "not_run")}`
- Source branch: `{source_sync.get("source_branch", "unknown")}`
- Synced folders: `{", ".join(source_sync.get("folders", [])) or "none"}`
- Synced files: `{", ".join(source_sync.get("files", [])) or "none"}`

## Policy Matrix

{markdown_table(numeric_matrix, policy_columns)}

## Execution Footprint

{markdown_table(jobs, launch_columns) if jobs else "No Hugging Face jobs launched yet."}

## Key Artifacts

{chr(10).join(f"- `{label}`: `{path}`" for label, path in key_paths)}

## Reproduction

```bash
python training/exquisite/collect_selfplay_rollouts.py --mode smoke --case-limit 6 --eval-case-limit 2 --num-generations 4
python training/exquisite/evaluate_exquisite_policy.py
python training/exquisite/plot_exquisite_training_results.py
python training/exquisite/build_exquisite_dashboard.py
python training/exquisite/render_exquisite_report.py
```

HF launch with source sync and token fallback:

```bash
export HF_TOKEN_PRIMARY="..."
export HF_TOKEN_SECONDARY="..."
python training/exquisite/launch_exquisite_jobs.py --monitor
```
"""
    return text


def main() -> None:
    args = parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    report = render_report(args)
    output = args.report_dir / "exquisite_training_report.md"
    output.write_text(report, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
