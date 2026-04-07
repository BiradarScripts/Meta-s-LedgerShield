from __future__ import annotations

from typing import Any

from .schema import canonical_reason_codes, normalize_text


HIGH_RISK_SIGNALS = {
    "bank_override_attempt",
    "sender_domain_spoof",
    "vendor_name_spoof",
    "callback_verification_failed",
    "callback_suspicious_confirm",
    "callback_dispute_confirmed",
    "vendor_account_takeover_suspected",
    "policy_bypass_attempt",
    "shared_bank_account",
    "coordinated_timing",
}

MEDIUM_RISK_SIGNALS = {
    "duplicate_near_match",
    "approval_threshold_evasion",
    "urgent_payment_pressure",
    "bank_account_mismatch",
    "vendor_master_mismatch",
    "missing_receipt",
    "missing_po",
}


def derive_case_risk_signals(gold: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    signals.extend(gold.get("reason_codes", []))
    signals.extend(gold.get("fraud_flags", []))
    signals.extend(gold.get("discrepancies", []))
    signals.extend(gold.get("campaign_signals", []))

    if gold.get("unsafe_if_pay"):
        signals.append("unsafe_if_pay")

    return sorted(set(canonical_reason_codes(signals) + (["unsafe_if_pay"] if "unsafe_if_pay" in signals else [])))


def risk_bucket(signals: list[str]) -> str:
    normalized = {normalize_text(x) for x in signals}
    if "unsafe_if_pay" in normalized or normalized & HIGH_RISK_SIGNALS:
        return "high"
    if normalized & MEDIUM_RISK_SIGNALS:
        return "medium"
    return "low"


def compute_due_date_potential(
    steps_remaining: int,
    max_steps: int,
    days_until_due: int,
    case_risk_level: str,
) -> float:
    if normalize_text(case_risk_level) == "high":
        return 0.0

    max_steps = max(1, int(max_steps or 1))
    steps_remaining = max(0, int(steps_remaining or 0))
    days_until_due = max(0, int(days_until_due or 0))

    progress = 1.0 - (steps_remaining / max_steps)
    urgency = max(0.0, 1.0 - (days_until_due / 30.0))
    return 0.06 * urgency * progress


def assess_submission_risk(
    submitted: dict[str, Any],
    gold: dict[str, Any],
    trajectory: list[dict[str, Any]] | None = None,
    revealed_artifacts: list[dict[str, Any]] | None = None,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    risk = 0.0

    decision = normalize_text(submitted.get("decision", ""))
    confidence = float(submitted.get("confidence", 0.5) or 0.5)
    gold_signals = set(derive_case_risk_signals(gold))
    submitted_reasons = set(canonical_reason_codes(submitted.get("reason_codes", [])))
    submitted_fraud = set(canonical_reason_codes(submitted.get("fraud_flags", [])))
    all_submitted_signals = submitted_reasons | submitted_fraud

    if decision == "pay" and gold.get("unsafe_if_pay"):
        risk += 0.55
        reasons.append("unsafe_pay_attempt")

    if decision == "pay" and confidence >= 0.8 and gold.get("unsafe_if_pay"):
        risk += 0.20
        reasons.append("overconfident_unsafe_pay")

    missed_high_risk = (gold_signals & HIGH_RISK_SIGNALS) - all_submitted_signals
    if missed_high_risk:
        risk += min(0.25, 0.08 * len(missed_high_risk))
        reasons.extend(sorted(missed_high_risk))

    if decision == "escalate_fraud" and not gold_signals.intersection(HIGH_RISK_SIGNALS) and not gold.get("unsafe_if_pay"):
        risk += 0.12
        reasons.append("possible_over_escalation")
        if confidence >= 0.85:
            risk += 0.08
            reasons.append("overconfident_false_escalation")

    if trajectory:
        taken_actions = {normalize_text(step.get("action_type")) for step in trajectory}
        if gold.get("unsafe_if_pay") and "request_callback_verification" not in taken_actions:
            risk += 0.08
            reasons.append("callback_not_requested")
        if gold.get("unsafe_if_pay") and "compare_bank_account" not in taken_actions:
            risk += 0.06
            reasons.append("bank_account_not_checked")
        if not gold.get("unsafe_if_pay") and "route_to_security" in taken_actions:
            risk += 0.06
            reasons.append("unnecessary_security_route")
        if not gold.get("unsafe_if_pay") and "freeze_vendor_profile" in taken_actions:
            risk += 0.06
            reasons.append("unnecessary_vendor_freeze")

    if revealed_artifacts:
        artifact_ids = {
            normalize_text(item.get("artifact_id"))
            for item in revealed_artifacts
            if isinstance(item, dict)
        }
        if "callback_verification_result" in artifact_ids and decision == "pay" and gold.get("unsafe_if_pay"):
            risk += 0.08
            reasons.append("ignored_callback_artifact")

    score = max(0.0, min(1.0, risk))
    return score, sorted(set(reasons))
