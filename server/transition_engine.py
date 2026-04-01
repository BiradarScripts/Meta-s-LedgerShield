from __future__ import annotations

from typing import Any

from models import LedgerShieldState

from .schema import normalize_text
from .world_state import register_observed_signals, reveal_artifact


def update_from_tool_result(
    state: LedgerShieldState,
    tool_name: str,
    result: dict[str, Any],
) -> int:
    signals: list[str] = []

    if tool_name == "lookup_vendor_history":
        signals.extend(result.get("derived_flags", []))
    elif tool_name == "search_ledger":
        if result.get("near_duplicate_count", 0) > 0:
            signals.append("duplicate_near_match")
    elif tool_name == "inspect_email_thread":
        thread = result.get("thread", {})
        signals.extend(thread.get("derived_flags", []))
    elif tool_name == "compare_bank_account":
        signals.extend(result.get("derived_flags", []))

    return register_observed_signals(state, signals)


def _build_handoff_packet(
    state: LedgerShieldState,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": state.case_id,
        "observed_risk_signals": list(state.observed_risk_signals),
        "revealed_artifact_ids": list(state.revealed_artifact_ids),
        "recommended_next_step": payload.get("recommended_next_step", "manual_review"),
        "summary": payload.get("summary", ""),
        "confidence": float(payload.get("confidence", 0.5) or 0.5),
    }


def handle_intervention(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
    action_type: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    artifact_id = None
    message = ""
    status = "completed"

    if action_type == "request_callback_verification":
        artifact_id = "callback_verification_result"
        message = "Callback verification requested."
    elif action_type == "freeze_vendor_profile":
        message = "Vendor profile frozen pending investigation."
    elif action_type == "request_bank_change_approval_chain":
        artifact_id = "bank_change_approval_chain"
        message = "Bank change approval chain requested."
    elif action_type == "request_po_reconciliation":
        artifact_id = "po_reconciliation_report"
        message = "PO reconciliation requested."
    elif action_type == "request_additional_receipt_evidence":
        artifact_id = "receipt_reconciliation_report"
        message = "Additional receipt evidence requested."
    elif action_type == "route_to_procurement":
        message = "Case routed to procurement."
    elif action_type == "route_to_security":
        message = "Case routed to security."
    elif action_type == "flag_duplicate_cluster_review":
        artifact_id = "duplicate_cluster_report"
        message = "Duplicate cluster review requested."
    elif action_type == "create_human_handoff":
        state.handoff_packet = _build_handoff_packet(state, payload)
        message = "Human handoff packet created."
    else:
        return {"error": f"unsupported intervention: {action_type}"}, [f"Unsupported intervention: {action_type}"]

    artifact = None
    if artifact_id:
        artifact = reveal_artifact(state, hidden_world, artifact_id)

    hidden_world.setdefault("intervention_status", {})[action_type] = {
        "status": status,
        "case_clock": state.case_clock,
    }

    event = {
        "action_type": action_type,
        "status": status,
        "payload": payload,
        "artifact_id": artifact_id,
    }
    state.interventions_taken.append(event)

    result = {
        "tool_name": action_type,
        "success": True,
        "intervention": True,
        "artifact": artifact,
        "message": message,
    }
    return result, [message]


def normalized_result_with_signals(
    state: LedgerShieldState,
    tool_name: str,
    raw: dict[str, Any],
    cost: float,
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(raw, dict):
        raw = {"payload": raw}

    success = "error" not in raw
    message = raw.get("message")
    if not message:
        message = f"{tool_name} completed." if success else str(raw.get("error", f"{tool_name} failed."))

    novel_signal_count = update_from_tool_result(state, tool_name, raw) if success else 0

    normalized = {
        "tool_name": tool_name,
        "success": success,
        **raw,
        "message": message,
        "cost": cost,
        "novel_signal_count": novel_signal_count,
    }
    return normalized, [message]