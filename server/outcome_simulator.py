from __future__ import annotations

from typing import Any


def simulate_outcome(
    submitted: dict[str, Any],
    trajectory: list[dict[str, Any]] | None = None,
    hidden_world: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trajectory = trajectory or []
    hidden_world = hidden_world or {}

    decision = str(submitted.get("decision", "NEEDS_REVIEW"))
    latent_outcomes = hidden_world.get("latent_outcomes", {})

    risky = latent_outcomes.get("PAY") == "unsafe_payment_released"
    actions_taken = {step.get("action_type") for step in trajectory}

    has_callback = "request_callback_verification" in actions_taken
    has_freeze = "freeze_vendor_profile" in actions_taken
    has_security_route = "route_to_security" in actions_taken
    has_duplicate_review = "flag_duplicate_cluster_review" in actions_taken
    has_handoff = "create_human_handoff" in actions_taken

    hardened = has_callback or has_freeze or has_security_route or has_duplicate_review

    if decision == "PAY":
        if risky and not hardened:
            return {
                "outcome_type": "unsafe_payment_released",
                "unsafe_payment": True,
                "score": 0.0,
                "summary": "Unsafe payment released because the case was risky and insufficient controls were applied.",
            }
        if risky and hardened:
            return {
                "outcome_type": "policy_breach",
                "unsafe_payment": True,
                "score": 0.15,
                "summary": "Payment was released despite elevated signals and partial investigation.",
            }
        return {
            "outcome_type": "safe_payment_cleared",
            "unsafe_payment": False,
            "score": 1.0,
            "summary": "Payment cleared safely.",
        }

    if decision in {"HOLD", "NEEDS_REVIEW"}:
        if risky:
            return {
                "outcome_type": "manual_review_created",
                "unsafe_payment": False,
                "score": 0.90 if has_callback or has_handoff else 0.82,
                "summary": "Risk was contained through manual review.",
            }
        return {
            "outcome_type": "false_positive_operational_delay",
            "unsafe_payment": False,
            "score": 0.42 if has_security_route or has_freeze else 0.52,
            "summary": "A clean payment was delayed unnecessarily.",
        }

    if decision == "ESCALATE_FRAUD":
        if risky:
            return {
                "outcome_type": "fraud_prevented",
                "unsafe_payment": False,
                "score": 1.0 if has_security_route or has_freeze else 0.94,
                "summary": "Fraud escalation prevented financial loss.",
            }
        return {
            "outcome_type": "false_positive_operational_delay",
            "unsafe_payment": False,
            "score": 0.30 if has_security_route or has_freeze else 0.38,
            "summary": "Fraud escalation was overly aggressive for a clean case.",
        }

    return {
        "outcome_type": latent_outcomes.get(decision, "manual_review_created"),
        "unsafe_payment": False,
        "score": 0.5,
        "summary": "Outcome defaulted.",
    }
