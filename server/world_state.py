from __future__ import annotations

from copy import deepcopy
from typing import Any

from models import LedgerShieldState

from .risk_rules import derive_case_risk_signals, risk_bucket
from .schema import normalize_text


def build_hidden_world(case: dict[str, Any]) -> dict[str, Any]:
    gold = case.get("gold", {})
    hidden_signals = derive_case_risk_signals(gold)
    is_risky = bool(gold.get("unsafe_if_pay")) or risk_bucket(hidden_signals) == "high"

    callback_status = "failed" if is_risky else "passed"
    bank_chain_status = "mismatch_found" if any(
        signal in hidden_signals
        for signal in {
            "bank_override_attempt",
            "callback_verification_failed",
            "vendor_account_takeover_suspected",
            "policy_bypass_attempt",
        }
    ) else "clean"

    duplicate_status = "cluster_detected" if any(
        signal in hidden_signals
        for signal in {"duplicate_near_match", "approval_threshold_evasion"}
    ) or gold.get("duplicate_links") else "no_cluster"

    po_status = "reconciled_with_flags" if any(
        signal in hidden_signals
        for signal in {
            "missing_po",
            "total_mismatch",
            "price_mismatch",
            "quantity_mismatch",
        }
    ) else "reconciled_clean"

    receipt_status = "reconciled_with_flags" if any(
        signal in hidden_signals
        for signal in {
            "missing_receipt",
            "partial_receipt_only",
            "receipt_date_mismatch",
        }
    ) else "reconciled_clean"

    return {
        "hidden_risk_signals": hidden_signals,
        "revealed_artifacts": {},
        "artifact_unlock_order": [],
        "intervention_status": {},
        "portfolio_memory": {
            "vendor_risk_bucket": risk_bucket(hidden_signals),
            "linked_case_count": len(gold.get("duplicate_links", [])),
        },
        "latent_outcomes": {
            "PAY": "unsafe_payment_released" if is_risky else "safe_payment_cleared",
            "HOLD": "manual_review_created" if is_risky else "false_positive_operational_delay",
            "NEEDS_REVIEW": "manual_review_created",
            "ESCALATE_FRAUD": "fraud_prevented" if is_risky else "false_positive_operational_delay",
        },
        "artifact_templates": {
            "callback_verification_result": {
                "artifact_id": "callback_verification_result",
                "artifact_type": "verification",
                "summary": f"Vendor callback verification {callback_status}.",
                "details": {
                    "status": callback_status,
                    "confidence": 0.92 if is_risky else 0.78,
                },
            },
            "bank_change_approval_chain": {
                "artifact_id": "bank_change_approval_chain",
                "artifact_type": "approval_chain",
                "summary": f"Bank change approval chain review: {bank_chain_status}.",
                "details": {
                    "status": bank_chain_status,
                    "requires_manual_callback": is_risky,
                },
            },
            "po_reconciliation_report": {
                "artifact_id": "po_reconciliation_report",
                "artifact_type": "reconciliation",
                "summary": f"PO reconciliation completed: {po_status}.",
                "details": {
                    "status": po_status,
                    "expected_discrepancies": deepcopy(gold.get("discrepancies", [])),
                },
            },
            "receipt_reconciliation_report": {
                "artifact_id": "receipt_reconciliation_report",
                "artifact_type": "reconciliation",
                "summary": f"Receipt reconciliation completed: {receipt_status}.",
                "details": {
                    "status": receipt_status,
                    "expected_discrepancies": deepcopy(gold.get("discrepancies", [])),
                },
            },
            "duplicate_cluster_report": {
                "artifact_id": "duplicate_cluster_report",
                "artifact_type": "duplicate_analysis",
                "summary": f"Duplicate cluster review result: {duplicate_status}.",
                "details": {
                    "status": duplicate_status,
                    "gold_links": deepcopy(gold.get("duplicate_links", [])),
                },
            },
        },
    }


def register_observed_signals(state: LedgerShieldState, candidates: list[str]) -> int:
    before = set(state.observed_risk_signals)
    for signal in candidates:
        norm = normalize_text(signal)
        if norm:
            state.observed_risk_signals.append(norm)
    state.observed_risk_signals = sorted(set(state.observed_risk_signals))
    after = set(state.observed_risk_signals)
    return len(after - before)


def reveal_artifact(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    template = hidden_world.get("artifact_templates", {}).get(artifact_id)
    if template is None:
        raise KeyError(f"Unknown artifact_id: {artifact_id}")

    artifact = deepcopy(template)
    hidden_world.setdefault("revealed_artifacts", {})[artifact_id] = artifact

    if artifact_id not in state.revealed_artifact_ids:
        state.revealed_artifact_ids.append(artifact_id)
        hidden_world.setdefault("artifact_unlock_order", []).append(artifact_id)

    details = artifact.get("details", {})
    status = normalize_text(details.get("status"))
    derived_signals: list[str] = []

    if artifact_id == "callback_verification_result" and status == "failed":
        derived_signals.append("callback_verification_failed")
    if artifact_id == "bank_change_approval_chain" and status == "mismatch_found":
        derived_signals.append("policy_bypass_attempt")
    if artifact_id == "duplicate_cluster_report" and status == "cluster_detected":
        derived_signals.append("duplicate_near_match")

    register_observed_signals(state, derived_signals)
    return artifact


def public_revealed_artifacts(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> list[dict[str, Any]]:
    revealed = hidden_world.get("revealed_artifacts", {})
    return [revealed[key] for key in state.revealed_artifact_ids if key in revealed]


def risk_snapshot(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> dict[str, Any]:
    observed = sorted(set(state.observed_risk_signals))
    hidden_bucket = risk_bucket(hidden_world.get("hidden_risk_signals", []))
    observed_bucket = risk_bucket(observed)
    return {
        "observed_risk_bucket": observed_bucket,
        "latent_risk_bucket": hidden_bucket,
        "observed_signals": observed,
        "observed_signal_count": len(observed),
    }


def investigation_status(state: LedgerShieldState) -> dict[str, Any]:
    investigation_actions = [
        step
        for step in state.trajectory
        if not step.get("is_intervention", False) and step.get("action_type") != "submit_decision"
    ]
    return {
        "tool_calls": len(investigation_actions),
        "interventions_taken": len(state.interventions_taken),
        "revealed_artifacts": len(state.revealed_artifact_ids),
        "budget_used": round(max(state.budget_total - state.budget_remaining, 0.0), 4),
    }