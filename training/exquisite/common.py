#!/usr/bin/env python3
"""Shared helpers for the LedgerShield Exquisite Training Layer."""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = REPO_ROOT / "training"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

import ledgershield_trl_training as sft  # noqa: E402
from server.data_loader import load_all  # noqa: E402


EXQUISITE_ROOT = REPO_ROOT / "artifacts" / "exquisite-training"
EXISTING_SFT_DIR = REPO_ROOT / "artifacts" / "trl-openenv-hf-a10g-qwen-rich"
PENDING = "PENDING"
POLICY_RUN_PROFILES = {
    "random_baseline": "reference baseline",
    "naive_baseline": "reference heuristic",
    "base_model": "pretrain baseline",
    "trained_model": "original SFT benchmark",
    "grpo_0_5b": "flagship additive run",
    "sft_1_5b": "fast-profile scaling run",
    "grpo_1_5b": "pending scaling run",
    "grpo_3b": "pending flagship scaling run",
    "dpo_falsifier": "artifact-complete distillation",
    "teacher_policy": "reference ceiling",
}

DEFAULT_REWARD_WEIGHTS = {
    "final_score": 0.45,
    "certificate_score": 0.15,
    "control_satisfied_resolution": 0.15,
    "institutional_utility": 0.10,
    "institutional_loss_score": 0.05,
    "parse_success": 0.10,
    "unsafe_release": -0.60,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return 0.0
        return value
    return str(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def maybe_float(value: Any) -> float | None:
    if value in (None, "", PENDING, "n/a", "N/A"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def apply_policy_run_profile(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    policy_key = str(payload.get("policy_key") or "")
    payload.setdefault("run_profile", POLICY_RUN_PROFILES.get(policy_key, ""))
    return payload


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_jsonable(row), sort_keys=True) + "\n")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str] | None = None) -> None:
    materialized = [to_jsonable(row) for row in rows]
    ensure_dir(path.parent)
    if columns is None:
        seen: list[str] = []
        for row in materialized:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        columns = seen
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in materialized:
            writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_db() -> dict[str, Any]:
    return load_all()


def load_sft_examples(sft_dir: Path = EXISTING_SFT_DIR) -> list[dict[str, Any]]:
    examples = read_jsonl(sft_dir / "openenv_sft_examples.jsonl")
    if examples:
        return examples
    metrics = read_json(sft_dir / "training_metrics.json", default={}) or {}
    cases = metrics.get("case_ids") or []
    db = load_db()
    output_dir = ensure_dir(EXQUISITE_ROOT / "bootstrap-sft-examples")
    examples, _ = sft.collect_live_examples(cases, db, output_dir)
    return examples


def split_examples(
    examples: list[dict[str, Any]], eval_limit: int, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return sft.split_examples_for_training(examples, eval_limit, seed)


def prompt_for_generation(prompt: str) -> str:
    return f"### LedgerShield Prompt\n{prompt}\n### JSON Action Plan\n"


def parse_completion(text: str) -> tuple[list[dict[str, Any]], bool, str]:
    return sft.parse_actions_from_completion(text)


def run_actions(
    case_id: str,
    actions: list[dict[str, Any]],
    db: dict[str, Any],
    *,
    parse_success: bool = True,
    parse_error: str = "",
    max_actions: int = 30,
) -> dict[str, Any]:
    return sft.run_action_plan(
        case_id,
        actions,
        db,
        parse_success=parse_success,
        parse_error=parse_error,
        max_actions=max_actions,
    )


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    return sft.summarize_results(results)


def reward_components_from_result(result: dict[str, Any]) -> dict[str, float]:
    return {
        "final_score": safe_float(result.get("score")),
        "certificate_score": safe_float(result.get("certificate_score")),
        "control_satisfied_resolution": safe_float(result.get("control_satisfied_resolution")),
        "institutional_utility": safe_float(result.get("institutional_utility")),
        "institutional_loss_score": safe_float(result.get("institutional_loss_score")),
        "parse_success": 1.0 if result.get("parse_success") else 0.0,
        "unsafe_release": 1.0 if result.get("unsafe_release") else 0.0,
    }


def environment_reward(
    result: dict[str, Any], weights: dict[str, float] | None = None
) -> tuple[float, dict[str, float]]:
    weights = dict(DEFAULT_REWARD_WEIGHTS if weights is None else weights)
    components = reward_components_from_result(result)
    reward = sum(weights.get(key, 0.0) * value for key, value in components.items())
    return round(clamp(reward, -1.0, 1.0), 6), components


def failure_reason(row: dict[str, Any]) -> str:
    parse_error = str(row.get("parse_error") or "").strip()
    if parse_error:
        return parse_error.split(":", 1)[0]
    if row.get("unsafe_release"):
        return "unsafe_release"
    result_class = str(row.get("result_class") or "").strip()
    if result_class:
        return result_class
    errors = row.get("errors") or []
    if errors:
        return str(errors[0]).split(":", 1)[0]
    return "valid_or_unclassified"


def load_existing_training_metrics(sft_dir: Path = EXISTING_SFT_DIR) -> dict[str, Any]:
    return read_json(sft_dir / "training_metrics.json", default={}) or {}


def policy_rows_from_existing_metrics(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "random_baseline": ("Random", "-", "baseline"),
        "naive_baseline": ("Naive PAY", "-", "baseline"),
        "base_model": ("Base Qwen", "0.5B", "base"),
        "trained_model": ("SFT Qwen", "0.5B", "SFT"),
        "teacher_policy": ("Teacher", "-", "oracle-ish"),
    }
    rows: list[dict[str, Any]] = []
    evaluations = metrics.get("evaluations", {}) or {}
    for key, (policy, model, method) in labels.items():
        summary = ((evaluations.get(key) or {}).get("summary") or {}) if isinstance(evaluations.get(key), dict) else {}
        if not summary:
            continue
        rows.append(
            apply_policy_run_profile(
                {
                    "policy_key": key,
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
                    "source": rel_path(EXISTING_SFT_DIR / "training_metrics.json"),
                }
            )
        )
    return rows


def per_case_rows_from_existing_metrics(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    evaluations = metrics.get("evaluations", {}) or {}
    examples = {
        str(((row.get("metadata") or {}).get("case_id"))): row
        for row in read_jsonl(EXISTING_SFT_DIR / "openenv_sft_examples.jsonl")
    }
    labels = {
        "random_baseline": "Random",
        "naive_baseline": "Naive PAY",
        "base_model": "Base Qwen 0.5B",
        "trained_model": "SFT Qwen 0.5B",
        "teacher_policy": "Teacher",
    }
    for policy_key, payload in evaluations.items():
        if policy_key not in labels or not isinstance(payload, dict):
            continue
        for result in payload.get("results", []) or []:
            case_id = str(result.get("case_id") or "")
            metadata = (examples.get(case_id) or {}).get("metadata", {}) or {}
            rows.append(
                {
                    "policy_key": policy_key,
                    "policy": labels[policy_key],
                    "case_id": case_id,
                    "task_type": metadata.get("task_type", "unknown"),
                    "score": safe_float(result.get("score")),
                    "certificate_score": safe_float(result.get("certificate_score")),
                    "control_satisfied_resolution": safe_float(result.get("control_satisfied_resolution")),
                    "unsafe_release": 1.0 if result.get("unsafe_release") else 0.0,
                    "parse_success": 1.0 if result.get("parse_success") else 0.0,
                    "result_class": result.get("result_class", ""),
                    "source": rel_path(EXISTING_SFT_DIR / "training_metrics.json"),
                }
            )
    return rows


def launch_status_path(report_dir: Path | None = None) -> Path:
    base_dir = EXQUISITE_ROOT / "reports" if report_dir is None else report_dir
    return base_dir / "hf_exquisite_launches.json"


def launch_jobs(report_dir: Path | None = None) -> list[dict[str, Any]]:
    payload = read_json(launch_status_path(report_dir), default={}) or {}
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [row for row in jobs if isinstance(row, dict)]


def live_launch_jobs(report_dir: Path | None = None) -> list[dict[str, Any]]:
    return [row for row in launch_jobs(report_dir) if not row.get("exclude_from_live_reports")]


JOB_ARTIFACT_SENTINELS: dict[str, tuple[Path, ...]] = {
    "selfplay-0.5b": (EXQUISITE_ROOT / "selfplay-0.5b" / "selfplay_candidates.jsonl",),
    "grpo-0.5b": (EXQUISITE_ROOT / "grpo-0.5b" / "final_policy_eval.json",),
    "dpo-falsifier-distill": (EXQUISITE_ROOT / "dpo-falsifier-distill" / "final_policy_eval.json",),
    "sft-1.5b": (EXQUISITE_ROOT / "sft-1.5b" / "training_metrics.json",),
}


def artifact_complete_for_job(row: dict[str, Any], artifact_root: Path | None = None) -> bool:
    base = EXQUISITE_ROOT if artifact_root is None else artifact_root
    name = str(row.get("name") or "")
    sentinels = JOB_ARTIFACT_SENTINELS.get(name, ())
    for sentinel in sentinels:
        candidate = base / sentinel.relative_to(EXQUISITE_ROOT)
        if candidate.exists():
            return True
    return False


def public_launch_row(row: dict[str, Any], artifact_root: Path | None = None) -> dict[str, Any]:
    payload = dict(row)
    raw_status = str(payload.get("last_status") or "").upper()
    if artifact_complete_for_job(payload, artifact_root):
        public_status = "COMPLETE"
        public_note = "artifact-complete"
    elif raw_status == "RUNNING":
        public_status = "RUNNING"
        public_note = "in progress"
    elif raw_status == "SCHEDULING":
        public_status = "SCHEDULING"
        public_note = "queued"
    elif raw_status == "CANCELED":
        public_status = "CANCELED"
        public_note = "not part of live scope"
    elif raw_status in {"ERROR", "DELETED"}:
        public_status = "INCOMPLETE"
        public_note = "artifact missing"
    else:
        public_status = raw_status or "UNKNOWN"
        public_note = ""
    payload["public_status"] = public_status
    payload["public_note"] = public_note
    payload.pop("last_message", None)
    payload.pop("last_status", None)
    payload.pop("recent_log_tail", None)
    payload.pop("url", None)
    payload.pop("id", None)
    payload.pop("namespace_used", None)
    payload.pop("token_used", None)
    payload.pop("token_redacted", None)
    payload.pop("launched_at", None)
    return payload


def public_live_launch_jobs(report_dir: Path | None = None, artifact_root: Path | None = None) -> list[dict[str, Any]]:
    return [public_launch_row(row, artifact_root) for row in live_launch_jobs(report_dir)]


def excluded_run_names(report_dir: Path | None = None) -> set[str]:
    jobs = launch_jobs(report_dir)
    names = {str(row.get("name") or "") for row in jobs}
    excluded: set[str] = set()
    for name in names:
        matching = [row for row in jobs if str(row.get("name") or "") == name]
        if matching and all(row.get("exclude_from_live_reports") for row in matching):
            excluded.add(name)
    return excluded


def pending_policy_rows(excluded_policy_keys: set[str] | None = None) -> list[dict[str, Any]]:
    rows = [
        {"policy_key": "grpo_0_5b", "policy": "GRPO Qwen", "model": "0.5B", "method": "SFT->GRPO"},
        {"policy_key": "sft_1_5b", "policy": "SFT Qwen", "model": "1.5B", "method": "SFT"},
        {"policy_key": "grpo_1_5b", "policy": "GRPO Qwen", "model": "1.5B", "method": "SFT->GRPO"},
        {"policy_key": "grpo_3b", "policy": "GRPO Qwen", "model": "3B", "method": "SFT+GRPO"},
        {"policy_key": "dpo_falsifier", "policy": "DPO-Falsifier", "model": "1.5B/3B", "method": "GRPO->DPO"},
    ]
    excluded = excluded_policy_keys or set()
    return [apply_policy_run_profile(row) for row in rows if str(row.get("policy_key") or "") not in excluded]


def fill_pending(row: dict[str, Any]) -> dict[str, Any]:
    payload = apply_policy_run_profile(row)
    for key in [
        "mean_score",
        "mean_total_reward",
        "certificate_score",
        "control_satisfied",
        "unsafe_release",
        "parse_success",
    ]:
        payload.setdefault(key, PENDING)
    payload.setdefault("status", PENDING)
    payload.setdefault("source", PENDING)
    return payload


def extract_job_url(job: Any) -> str:
    return str(getattr(job, "url", "") or getattr(job, "id", "") or job)


def redact_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def token_from_env(primary: bool = True) -> str:
    names = ["HF_TOKEN_PRIMARY", "HF_TOKEN"] if primary else ["HF_TOKEN_SECONDARY"]
    for name in names:
        token = os.environ.get(name)
        if token:
            return token
    return ""
