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
    intervention_actions = {
        "request_callback_verification",
        "freeze_vendor_profile",
        "request_bank_change_approval_chain",
        "request_po_reconciliation",
        "request_additional_receipt_evidence",
        "route_to_procurement",
        "route_to_security",
        "flag_duplicate_cluster_review",
        "create_human_handoff",
    }
    taken_interventions = actions & intervention_actions

    score = 0.35
    if risky and "request_callback_verification" in actions:
        score += 0.20
    if risky and "route_to_security" in actions and decision == "escalate_fraud":
        score += 0.15
    if risky and "freeze_vendor_profile" in actions:
        score += 0.10
    if risky and "flag_duplicate_cluster_review" in actions:
        score += 0.10
    if risky and not taken_interventions:
        score -= 0.15

    if not risky and decision == "pay" and not taken_interventions:
        score += 0.30
    if not risky and "request_callback_verification" in actions:
        score -= 0.08
    if not risky and "route_to_security" in actions:
        score -= 0.18
    if not risky and "freeze_vendor_profile" in actions:
        score -= 0.18
    if not risky and "flag_duplicate_cluster_review" in actions:
        score -= 0.10
    if outcome and outcome.get("unsafe_payment"):
        score -= 0.3

    return max(0.0, min(1.0, score))


def efficiency_score(
    budget_penalty: float,
    trajectory: list[dict[str, Any]] | None,
) -> float:
    repeat_penalty = 0.0
    length_penalty = 0.0
    if trajectory:
        seen: dict[tuple[str, str], int] = {}
        for step in trajectory:
            action_type = normalize_text(step.get("action_type"))
            signature = normalize_text(str(step.get("payload", {})))
            key = (action_type, signature)
            seen[key] = seen.get(key, 0) + 1
        repeats = sum(max(0, count - 1) for count in seen.values())
        repeat_penalty = min(0.25, repeats * 0.03)
        if len(trajectory) > 8:
            length_penalty = min(0.12, (len(trajectory) - 8) * 0.02)

    return max(0.0, min(1.0, 1.0 - budget_penalty - repeat_penalty - length_penalty))


def downstream_outcome_score(outcome: dict[str, Any] | None) -> float:
    if not outcome:
        return 0.5
    return float(max(0.0, min(1.0, outcome.get("score", 0.5))))


def resolution_state_score(
    submitted: dict[str, Any],
    final_state: dict[str, Any] | None,
    gold: dict[str, Any],
    outcome: dict[str, Any] | None,
) -> float:
    if not final_state:
        return 0.0

    actions = {normalize_text(action) for action in final_state.get("successful_actions", [])}
    revealed = {normalize_text(value) for value in final_state.get("revealed_artifact_ids", [])}
    required_actions = {normalize_text(value) for value in final_state.get("required_actions", [])}
    required_artifacts = {normalize_text(value) for value in final_state.get("required_artifacts", [])}
    decision = normalize_text(submitted.get("decision"))
    risky = bool(gold.get("unsafe_if_pay"))
    readiness = float(final_state.get("decision_readiness", 0.0) or 0.0)
    pending_events = int(final_state.get("pending_event_count", 0) or 0)

    action_cov = 1.0 if not required_actions else len(required_actions & actions) / max(len(required_actions), 1)
    artifact_cov = 1.0 if not required_artifacts else len(required_artifacts & revealed) / max(len(required_artifacts), 1)

    handoff_packet = final_state.get("handoff_packet", {}) or {}
    handoff_quality = 0.0
    if handoff_packet:
        handoff_fields = [
            normalize_text(handoff_packet.get("summary")),
            normalize_text(handoff_packet.get("recommended_next_step")),
            normalize_text(str(handoff_packet.get("observed_risk_signals", []))),
        ]
        handoff_quality = sum(bool(field) for field in handoff_fields) / len(handoff_fields)

    score = 0.20 + 0.25 * action_cov + 0.20 * artifact_cov + 0.15 * readiness + 0.10 * handoff_quality

    if risky and decision in {"hold", "needs_review", "escalate_fraud"}:
        score += 0.08
    if risky and pending_events > 0 and decision == "pay":
        score -= 0.20
    if not risky and decision == "pay":
        score += 0.08
    if not risky and {"route_to_security", "freeze_vendor_profile"} & actions:
        score -= 0.15
    if outcome and normalize_text(outcome.get("outcome_type")) == "fraud_prevented":
        score += 0.05
    if outcome and normalize_text(outcome.get("outcome_type")) == "safe_payment_cleared":
        score += 0.05

    return max(0.0, min(1.0, score))
