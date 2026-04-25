from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .benchmark_contract import HUMAN_BASELINE_TRACK, track_label

DEFAULT_HUMAN_BASELINE_PATH = Path(os.getenv("LEDGERSHIELD_HUMAN_BASELINE_PATH", "artifacts/human_baseline.json"))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mean(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return round(sum(_safe_float(row.get(field)) for row in rows) / max(len(rows), 1), 4)


def empty_human_baseline_summary(note: str) -> dict[str, Any]:
    return {
        "track": HUMAN_BASELINE_TRACK,
        "track_label": track_label(HUMAN_BASELINE_TRACK),
        "participant_count": 0,
        "case_count": 0,
        "accuracy": 0.0,
        "avg_minutes_per_case": 0.0,
        "escalation_rate": 0.0,
        "evidence_citation_rate": 0.0,
        "false_positive_rate": 0.0,
        "fraud_miss_rate": 0.0,
        "calibration_score": 0.0,
        "participants": [],
        "note": note,
    }


def load_human_baseline_summary(path: str | Path | None = None) -> dict[str, Any]:
    baseline_path = Path(path or DEFAULT_HUMAN_BASELINE_PATH)
    if not baseline_path.exists():
        return empty_human_baseline_summary(
            "No human baseline artifact found. Provide artifacts/human_baseline.json or set LEDGERSHIELD_HUMAN_BASELINE_PATH.",
        )

    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty_human_baseline_summary("Human baseline artifact exists but is not valid JSON.")

    participants = payload.get("participants", []) or []
    normalized_rows: list[dict[str, Any]] = []
    for index, participant in enumerate(participants, start=1):
        if not isinstance(participant, dict):
            continue
        normalized_rows.append(
            {
                "participant_id": str(participant.get("participant_id") or f"human-{index}"),
                "role": str(participant.get("role") or "unknown"),
                "case_count": int(participant.get("case_count", 0) or 0),
                "accuracy": _safe_float(participant.get("accuracy")),
                "avg_minutes_per_case": _safe_float(participant.get("avg_minutes_per_case")),
                "escalation_rate": _safe_float(participant.get("escalation_rate")),
                "evidence_citation_rate": _safe_float(participant.get("evidence_citation_rate")),
                "false_positive_rate": _safe_float(participant.get("false_positive_rate")),
                "fraud_miss_rate": _safe_float(participant.get("fraud_miss_rate")),
                "calibration_score": _safe_float(participant.get("calibration_score")),
            }
        )

    if not normalized_rows:
        return empty_human_baseline_summary("Human baseline artifact loaded, but it contains no valid participants.")

    return {
        "track": HUMAN_BASELINE_TRACK,
        "track_label": track_label(HUMAN_BASELINE_TRACK),
        "participant_count": len(normalized_rows),
        "case_count": sum(int(row.get("case_count", 0) or 0) for row in normalized_rows),
        "accuracy": _mean(normalized_rows, "accuracy"),
        "avg_minutes_per_case": _mean(normalized_rows, "avg_minutes_per_case"),
        "escalation_rate": _mean(normalized_rows, "escalation_rate"),
        "evidence_citation_rate": _mean(normalized_rows, "evidence_citation_rate"),
        "false_positive_rate": _mean(normalized_rows, "false_positive_rate"),
        "fraud_miss_rate": _mean(normalized_rows, "fraud_miss_rate"),
        "calibration_score": _mean(normalized_rows, "calibration_score"),
        "participants": normalized_rows,
        "note": str(payload.get("note") or ""),
        "source_path": str(baseline_path),
    }
