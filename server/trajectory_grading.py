from __future__ import annotations

from typing import Any

from .schema import normalize_text


def calibration_score(submitted: dict[str, Any], gold: dict[str, Any]) -> float:
    confidence = float(submitted.get("confidence", 0.5) or 0.5)
    confidence = max(0.0, min(1.0, confidence))
    decision = normalize_text(submitted.get("decision"))
    risky = bool(gold.get("unsafe_if_pay"))

    if risky and decision == "pay":
        return max(0.0, 0.5 - confidence)
    if risky and decision in {"hold", "needs_review", "escalate_fraud"}:
        return 0.6 + 0.4 * confidence
    if not risky and decision == "escalate_fraud":
        return 1.0 - 0.6 * confidence
    return 0.75 + 0.25 * confidence


def investigation_score(
    task_type: str,
    trajectory: list[dict[str, Any]] | None,
    gold: dict[str, Any],
) -> float:
    if not trajectory:
        return 0.0

    actions = {
        normalize_text(step.get("action_type"))
        for step in trajectory
        if step.get("success", True)
    }

    required_by_task = {
        "task_a": {"ocr", "zoom"},
        "task_b": {"lookup_po", "lookup_receipt", "lookup_policy"},
        "task_c": {"search_ledger", "compare_bank_account"},
        "task_d": {"inspect_email_thread", "lookup_vendor_history", "lookup_policy", "compare_bank_account"},
    }
    required = required_by_task.get(task_type, set())
    if gold.get("unsafe_if_pay"):
        required = set(required) | {"request_callback_verification"}

    if not required:
        return 1.0

    covered = len(required & actions) / len(required)
    return max(0.0, min(1.0, covered))


def intervention_score(
    submitted: dict[str, Any],
    trajectory: list[dict[str, Any]] | None,
    gold: dict[str, Any],
    outcome: dict[str, Any] | None,
) -> float:
    if not trajectory:
        return 0.0

    actions = {
        normalize_text(step.get("action_type"))
        for step in trajectory
        if step.get("success", True)
    }
    decision = normalize_text(submitted.get("decision"))
    risky = bool(gold.get("unsafe_if_pay"))

    score = 0.4
    if risky and "request_callback_verification" in actions:
        score += 0.2
    if risky and "route_to_security" in actions and decision == "escalate_fraud":
        score += 0.2
    if risky and "freeze_vendor_profile" in actions:
        score += 0.1
    if not risky and "route_to_security" in actions and decision == "escalate_fraud":
        score -= 0.2
    if outcome and outcome.get("unsafe_payment"):
        score -= 0.3

    return max(0.0, min(1.0, score))


def efficiency_score(
    budget_penalty: float,
    trajectory: list[dict[str, Any]] | None,
) -> float:
    repeat_penalty = 0.0
    if trajectory:
        seen: dict[tuple[str, str], int] = {}
        for step in trajectory:
            action_type = normalize_text(step.get("action_type"))
            signature = normalize_text(str(step.get("payload", {})))
            key = (action_type, signature)
            seen[key] = seen.get(key, 0) + 1
        repeats = sum(max(0, count - 1) for count in seen.values())
        repeat_penalty = min(0.25, repeats * 0.03)

    return max(0.0, min(1.0, 1.0 - budget_penalty - repeat_penalty))


def downstream_outcome_score(outcome: dict[str, Any] | None) -> float:
    if not outcome:
        return 0.5
    return float(max(0.0, min(1.0, outcome.get("score", 0.5))))