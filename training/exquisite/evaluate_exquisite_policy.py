#!/usr/bin/env python3
"""Build the combined Exquisite policy matrix and evaluation artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import (
        EXQUISITE_ROOT,
        PENDING,
        apply_policy_run_profile,
        excluded_run_names,
        fill_pending,
        failure_reason,
        load_existing_training_metrics,
        pending_policy_rows,
        per_case_rows_from_existing_metrics,
        policy_rows_from_existing_metrics,
        read_json,
        read_jsonl,
        rel_path,
        safe_float,
        to_jsonable,
        utc_now,
        write_csv,
        write_json,
        write_jsonl,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        EXQUISITE_ROOT,
        PENDING,
        apply_policy_run_profile,
        excluded_run_names,
        fill_pending,
        failure_reason,
        load_existing_training_metrics,
        pending_policy_rows,
        per_case_rows_from_existing_metrics,
        policy_rows_from_existing_metrics,
        read_json,
        read_jsonl,
        rel_path,
        safe_float,
        to_jsonable,
        utc_now,
        write_csv,
        write_json,
        write_jsonl,
    )


RUN_HINTS = {
    "grpo-0.5b": ("grpo_0_5b", "GRPO Qwen", "0.5B", "SFT->GRPO"),
    "sft-1.5b": ("sft_1_5b", "SFT Qwen", "1.5B", "SFT"),
    "grpo-1.5b": ("grpo_1_5b", "GRPO Qwen", "1.5B", "SFT->GRPO"),
    "grpo-3b-flagship": ("grpo_3b", "GRPO Qwen", "3B", "SFT+GRPO"),
    "dpo-falsifier-distill": ("dpo_falsifier", "DPO-Falsifier", "1.5B/3B", "GRPO->DPO"),
}

MATRIX_COLUMNS = [
    "policy_key",
    "policy",
    "model",
    "method",
    "run_profile",
    "mean_score",
    "mean_total_reward",
    "certificate_score",
    "control_satisfied",
    "unsafe_release",
    "parse_success",
    "status",
    "source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Exquisite evaluation matrix.")
    parser.add_argument("--artifact-root", type=Path, default=EXQUISITE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=EXQUISITE_ROOT / "reports")
    return parser.parse_args()


def summary_to_row(
    policy_key: str,
    policy: str,
    model: str,
    method: str,
    summary: dict[str, Any],
    source: Path,
) -> dict[str, Any]:
    return apply_policy_run_profile(
        {
        "policy_key": policy_key,
        "policy": policy,
        "model": model,
        "method": method,
        "mean_score": f"{safe_float(summary.get('mean_score')):.4f}",
        "mean_total_reward": f"{safe_float(summary.get('mean_total_reward')):.4f}",
        "certificate_score": f"{safe_float(summary.get('certificate_score_mean')):.4f}",
        "control_satisfied": f"{safe_float(summary.get('control_satisfied_resolution_rate')):.4f}",
        "unsafe_release": f"{safe_float(summary.get('unsafe_release_rate')):.4f}",
        "parse_success": f"{safe_float(summary.get('parse_success_rate')):.4f}",
        "status": "completed",
        "source": rel_path(source),
        }
    )


def row_from_run_dir(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    hint = RUN_HINTS.get(path.name)
    if not hint:
        return None, []
    policy_key, policy, model, method = hint
    eval_path = path / "final_policy_eval.json"
    payload = read_json(eval_path, default={}) or {}
    summary = payload.get("summary") if isinstance(payload, dict) else None
    if not isinstance(summary, dict):
        metrics = read_json(path / "training_metrics.json", default={}) or {}
        trained_eval = ((metrics.get("evaluations") or {}).get("trained_model") or {}) if isinstance(metrics, dict) else {}
        summary = trained_eval.get("summary") if isinstance(trained_eval, dict) else None
        eval_path = path / "training_metrics.json"
        payload = trained_eval if isinstance(trained_eval, dict) else {}
    if not isinstance(summary, dict) or not summary:
        return None, []
    per_case: list[dict[str, Any]] = []
    for result in payload.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        per_case.append(
            {
                "policy_key": policy_key,
                "policy": f"{policy} {model}",
                "case_id": result.get("case_id", ""),
                "task_type": result.get("task_type", "unknown"),
                "score": safe_float(result.get("score")),
                "certificate_score": safe_float(result.get("certificate_score")),
                "control_satisfied_resolution": safe_float(result.get("control_satisfied_resolution")),
                "unsafe_release": 1.0 if result.get("unsafe_release") else 0.0,
                "parse_success": 1.0 if result.get("parse_success") else 0.0,
                "result_class": result.get("result_class", ""),
                "source": rel_path(eval_path),
            }
        )
    return summary_to_row(policy_key, policy, model, method, summary, eval_path), per_case


def merge_policy_rows(
    existing: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
    excluded_policy_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded = excluded_policy_keys or set()
    rows_by_key = {row["policy_key"]: fill_pending(apply_policy_run_profile(row)) for row in existing}
    for row in pending_policy_rows(excluded):
        rows_by_key.setdefault(row["policy_key"], fill_pending(row))
    for row in discovered:
        rows_by_key[row["policy_key"]] = fill_pending(apply_policy_run_profile(row))
    order = [
        "random_baseline",
        "naive_baseline",
        "base_model",
        "trained_model",
        "grpo_0_5b",
        "sft_1_5b",
        "grpo_1_5b",
        "grpo_3b",
        "dpo_falsifier",
        "teacher_policy",
    ]
    order = [key for key in order if key not in excluded]
    ordered = [rows_by_key[key] for key in order if key in rows_by_key]
    ordered.extend(row for key, row in sorted(rows_by_key.items()) if key not in order and key not in excluded)
    return ordered


def build_per_task_rows(per_case: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in per_case:
        groups.setdefault((str(row.get("policy")), str(row.get("task_type") or "unknown")), []).append(row)
    rows: list[dict[str, Any]] = []
    for (policy, task_type), values in sorted(groups.items()):
        count = max(len(values), 1)
        rows.append(
            {
                "policy": policy,
                "task_type": task_type,
                "case_count": len(values),
                "mean_score": round(sum(safe_float(row.get("score")) for row in values) / count, 4),
                "mean_certificate_score": round(sum(safe_float(row.get("certificate_score")) for row in values) / count, 4),
                "unsafe_release_rate": round(sum(safe_float(row.get("unsafe_release")) for row in values) / count, 4),
                "parse_success_rate": round(sum(safe_float(row.get("parse_success")) for row in values) / count, 4),
            }
        )
    return rows


def build_failure_taxonomy(per_case: list[dict[str, Any]], selfplay_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in per_case:
        key = str(row.get("result_class") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    selfplay_counts: dict[str, int] = {}
    for row in selfplay_rows:
        result = row.get("result") if isinstance(row.get("result"), dict) else row
        key = str(row.get("failure_reason") or failure_reason(result))
        selfplay_counts[key] = selfplay_counts.get(key, 0) + 1
    return {
        "generated_at": utc_now(),
        "policy_result_class_counts": counts,
        "selfplay_failure_reason_counts": selfplay_counts,
    }


def default_ablation_results() -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "status": "pending_hf_runs",
        "ablations": [
            {"name": "without_certificate_bonus", "status": PENDING},
            {"name": "without_unsafe_penalty", "status": PENDING},
            {"name": "without_parse_bonus", "status": PENDING},
            {"name": "num_generations", "status": PENDING},
            {"name": "model_size", "status": PENDING},
            {"name": "sft_checkpoint_vs_base_start", "status": PENDING},
            {"name": "grpo_steps", "status": PENDING},
            {"name": "temperature", "status": PENDING},
            {"name": "dpo_after_grpo", "status": PENDING},
        ],
    }


def artifact_inventory(root: Path, report_dir: Path, run_names: list[str]) -> str:
    paths = [
        report_dir / "exquisite_training_summary.json",
        report_dir / "final_policy_matrix.csv",
        report_dir / "final_policy_matrix.json",
        report_dir / "per_case_results.jsonl",
        report_dir / "per_task_results.csv",
        report_dir / "failure_taxonomy.json",
        report_dir / "ablation_results.json",
    ]
    rows = ["# Exquisite Training Artifact Inventory", "", f"Generated at: `{utc_now()}`", ""]
    rows.extend(f"- `{rel_path(path)}`" for path in paths)
    for name in sorted(run_names):
        rows.append(f"- `{rel_path(root / name)}/`")
    text = "\n".join(rows) + "\n"
    (report_dir / "artifact_inventory.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    excluded_runs = excluded_run_names(args.output_dir)
    excluded_policy_keys = {RUN_HINTS[name][0] for name in excluded_runs if name in RUN_HINTS}
    active_run_hints = {name: hint for name, hint in RUN_HINTS.items() if name not in excluded_runs}
    existing_metrics = load_existing_training_metrics()
    existing_rows = policy_rows_from_existing_metrics(existing_metrics)
    per_case = per_case_rows_from_existing_metrics(existing_metrics)
    discovered_rows: list[dict[str, Any]] = []
    for run_name in active_run_hints:
        row, run_per_case = row_from_run_dir(args.artifact_root / run_name)
        if row:
            discovered_rows.append(row)
        per_case.extend(run_per_case)
    matrix = merge_policy_rows(existing_rows, discovered_rows, excluded_policy_keys)
    per_task = build_per_task_rows(per_case)
    selfplay_rows: list[dict[str, Any]] = []
    for path in [args.artifact_root / "selfplay-0.5b" / "selfplay_candidates.jsonl"]:
        selfplay_rows.extend(read_jsonl(path))
    failure_taxonomy = build_failure_taxonomy(per_case, selfplay_rows)
    ablations_path = args.output_dir / "ablation_results.json"
    ablations = read_json(ablations_path, default=None) or default_ablation_results()
    completed_count = sum(1 for row in matrix if row.get("status") == "completed")
    pending_count = sum(1 for row in matrix if row.get("status") != "completed")
    if excluded_runs:
        if pending_count:
            note = (
                "Current Exquisite report scope focuses on the additive runs that are still collecting final artifacts."
            )
            summary_status = "completed_with_pending_new_runs"
        else:
            note = "Current Exquisite report scope covers the completed additive run set and preserves the original SFT benchmark unchanged."
            summary_status = "completed"
    else:
        if pending_count:
            note = "New GRPO/DPO rows remain PENDING until Hugging Face jobs upload final_policy_eval.json artifacts."
            summary_status = "completed_with_pending_new_runs"
        else:
            note = "All live-scope policy rows are complete."
            summary_status = "completed"
    summary = {
        "generated_at": utc_now(),
        "status": summary_status,
        "policy_count": len(matrix),
        "completed_policy_count": completed_count,
        "pending_policy_count": pending_count,
        "per_case_row_count": len(per_case),
        "selfplay_candidate_count": len(selfplay_rows),
        "matrix_path": rel_path(args.output_dir / "final_policy_matrix.csv"),
        "excluded_runs": sorted(excluded_runs),
        "fast_profile_scaling_note": "The SFT Qwen 1.5B row is a fast-profile scaling run included as supporting model-scaling evidence, not the flagship apples-to-apples comparison.",
        "note": note,
    }
    write_csv(args.output_dir / "final_policy_matrix.csv", matrix, MATRIX_COLUMNS)
    write_json(args.output_dir / "final_policy_matrix.json", matrix)
    write_jsonl(args.output_dir / "per_case_results.jsonl", per_case)
    write_csv(args.output_dir / "per_task_results.csv", per_task)
    write_json(args.output_dir / "failure_taxonomy.json", failure_taxonomy)
    write_json(args.output_dir / "ablation_results.json", ablations)
    write_json(args.output_dir / "exquisite_training_summary.json", summary)
    artifact_inventory(args.artifact_root, args.output_dir, list(active_run_hints))
    print(json.dumps(to_jsonable(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
