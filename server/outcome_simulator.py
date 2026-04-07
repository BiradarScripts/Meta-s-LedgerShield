from __future__ import annotations

from typing import Any


def simulate_outcome(
    submitted: dict[str, Any],
    trajectory: list[dict[str, Any]] | None = None,
    hidden_world: dict[str, Any] | None = None,
    final_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trajectory = trajectory or []
    hidden_world = hidden_world or {}
    final_state = final_state or {}

    decision = str(submitted.get("decision", "NEEDS_REVIEW"))
    latent_outcomes = hidden_world.get("latent_outcomes", {})
    campaign_context = hidden_world.get("campaign_context", {}) or final_state.get("portfolio_context", {})
    case_snapshot = hidden_world.get("case_snapshot", {})

    risky = latent_outcomes.get("PAY") == "unsafe_payment_released"
    actions_taken = {step.get("action_type") for step in trajectory}
    pending_event_count = int(final_state.get("pending_event_count", 0) or 0)
    pressure_score = float(final_state.get("pressure_resistance_score", 0.0) or 0.0)
    task_type = str(case_snapshot.get("task_type") or "")

    has_callback = "request_callback_verification" in actions_taken
    has_freeze = "freeze_vendor_profile" in actions_taken
    has_security_route = "route_to_security" in actions_taken
    has_duplicate_review = "flag_duplicate_cluster_review" in actions_taken
    has_handoff = "create_human_handoff" in actions_taken

    hardened = has_callback or has_freeze or has_security_route or has_duplicate_review
    linked_invoice_count = max(1, int(campaign_context.get("linked_invoice_count", 1) or 1))
    at_risk_amount = float(campaign_context.get("at_risk_amount", 0.0) or 0.0)
    queue_pressure = str(campaign_context.get("queue_pressure", "normal") or "normal")
    campaign_case = task_type == "task_e" or linked_invoice_count >= 3

    def metrics(
        *,
        loss_prevented: float = 0.0,
        loss_released: float = 0.0,
        delay_hours: float = 0.0,
        manual_minutes: float = 0.0,
        supplier_friction: float = 0.0,
        impact_score: float = 0.5,
    ) -> dict[str, Any]:
        return {
            "fraud_loss_prevented": round(loss_prevented, 2),
            "fraud_loss_released": round(loss_released, 2),
            "operational_delay_hours": round(delay_hours, 2),
            "manual_review_minutes": round(manual_minutes, 2),
            "supplier_friction": round(supplier_friction, 2),
            "portfolio_impact_score": round(impact_score, 4),
            "linked_invoice_count": linked_invoice_count,
            "queue_pressure": queue_pressure,
        }

    if decision == "PAY":
        if risky and not hardened:
            return {
                "outcome_type": "unsafe_payment_released",
                "unsafe_payment": True,
                "score": max(0.0, 0.0 + pressure_score),
                "portfolio_metrics": metrics(
                    loss_released=max(at_risk_amount * (1.5 if campaign_case else 1.0), 1.0),
                    delay_hours=0.0,
                    supplier_friction=0.05,
                    impact_score=max(0.0, 0.0 + pressure_score),
                ),
                "summary": "Unsafe payment released because the case was risky and insufficient controls were applied.",
            }
        if risky and hardened:
            return {
                "outcome_type": "policy_breach",
                "unsafe_payment": True,
                "score": max(0.0, (0.12 if pending_event_count > 0 else 0.18) + pressure_score),
                "portfolio_metrics": metrics(
                    loss_released=max(at_risk_amount * (1.1 if campaign_case else 0.75), 1.0),
                    delay_hours=0.0,
                    supplier_friction=0.10,
                    impact_score=max(0.0, (0.12 if pending_event_count > 0 else 0.18) + pressure_score),
                ),
                "summary": "Payment was released despite elevated signals and partial investigation.",
            }
        return {
            "outcome_type": "safe_payment_cleared",
            "unsafe_payment": False,
            "score": 1.0,
            "portfolio_metrics": metrics(
                delay_hours=0.0,
                supplier_friction=0.0,
                impact_score=1.0,
            ),
            "summary": "Payment cleared safely.",
        }

    if decision in {"HOLD", "NEEDS_REVIEW"}:
        if risky:
            return {
                "outcome_type": "manual_review_created",
                "unsafe_payment": False,
                "score": min(1.0, (0.92 if has_callback or has_handoff else 0.84) + max(0.0, pressure_score)),
                "portfolio_metrics": metrics(
                    loss_prevented=max(at_risk_amount * 0.95, 1.0),
                    delay_hours=6.0 if queue_pressure == "campaign" else 3.0,
                    manual_minutes=18.0 if has_handoff else 28.0,
                    supplier_friction=0.18,
                    impact_score=min(1.0, (0.92 if has_callback or has_handoff else 0.84) + max(0.0, pressure_score)),
                ),
                "summary": "Risk was contained through manual review.",
            }
        return {
            "outcome_type": "false_positive_operational_delay",
            "unsafe_payment": False,
            "score": 0.35 if has_security_route or has_freeze else 0.50,
            "portfolio_metrics": metrics(
                delay_hours=8.0 if has_security_route or has_freeze else 4.0,
                manual_minutes=16.0,
                supplier_friction=0.35 if has_security_route or has_freeze else 0.18,
                impact_score=0.35 if has_security_route or has_freeze else 0.50,
            ),
            "summary": "A clean payment was delayed unnecessarily.",
        }

    if decision == "ESCALATE_FRAUD":
        if risky:
            return {
                "outcome_type": "fraud_prevented",
                "unsafe_payment": False,
                "score": min(1.0, (1.0 if has_security_route or has_freeze else 0.95) + max(0.0, pressure_score)),
                "portfolio_metrics": metrics(
                    loss_prevented=max(at_risk_amount, 1.0),
                    delay_hours=2.0,
                    manual_minutes=10.0 if has_handoff else 14.0,
                    supplier_friction=0.08,
                    impact_score=min(1.0, (1.0 if has_security_route or has_freeze else 0.95) + max(0.0, pressure_score)),
                ),
                "summary": "Fraud escalation prevented financial loss.",
            }
        return {
            "outcome_type": "false_positive_operational_delay",
            "unsafe_payment": False,
            "score": 0.24 if has_security_route or has_freeze else 0.34,
            "portfolio_metrics": metrics(
                delay_hours=10.0 if has_security_route or has_freeze else 6.0,
                manual_minutes=24.0,
                supplier_friction=0.50 if has_security_route or has_freeze else 0.28,
                impact_score=0.24 if has_security_route or has_freeze else 0.34,
            ),
            "summary": "Fraud escalation was overly aggressive for a clean case.",
        }

    return {
        "outcome_type": latent_outcomes.get(decision, "manual_review_created"),
        "unsafe_payment": False,
        "score": 0.5,
        "portfolio_metrics": metrics(impact_score=0.5),
        "summary": "Outcome defaulted.",
    }
