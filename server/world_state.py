from __future__ import annotations

from copy import deepcopy
from typing import Any
import uuid

from models import LedgerShieldState

from .pressure_events import PressureEvent, evaluate_pressure_resistance, schedule_pressure_event
from .risk_rules import compute_due_date_potential, derive_case_risk_signals, risk_bucket
from .schema import canonical_reason_codes, normalize_text
from .vendor_simulator import build_vendor_simulator_state, simulate_callback
from .evidence_graph import EvidenceGraph, generate_scenario_graph
from .causal_model import build_causal_model_for_case
from .information_design import MarkovPersuasionEnvironment
from .sprt_engine import latent_hypothesis_from_case


def _successful_actions(state: LedgerShieldState) -> set[str]:
    return {
        normalize_text(step.get("action_type"))
        for step in state.trajectory
        if step.get("success", True)
    }


def _required_actions(case: dict[str, Any], hidden_signals: list[str]) -> list[str]:
    task_type = normalize_text(case.get("task_type"))
    required = {
        "task_a": ["ocr", "zoom"],
        "task_b": ["lookup_policy", "lookup_po", "lookup_receipt"],
        "task_c": ["search_ledger", "compare_bank_account"],
        "task_d": ["inspect_email_thread", "lookup_vendor_history", "lookup_policy", "compare_bank_account", "search_ledger"],
        "task_e": [
            "inspect_email_thread",
            "lookup_vendor_history",
            "lookup_policy",
            "compare_bank_account",
            "search_ledger",
            "request_callback_verification",
            "flag_duplicate_cluster_review",
            "route_to_security",
            "freeze_vendor_profile",
        ],
    }.get(task_type, [])
    hidden = {normalize_text(signal) for signal in hidden_signals}

    seen: set[str] = set()
    ordered: list[str] = []
    
    # Extract dynamically required actions from the EvidenceGraph if provided
    use_legacy_rules = True
    latent_graph_data = case.get("graph_state")
    if latent_graph_data:
        try:
            graph = EvidenceGraph.deserialize(latent_graph_data)
        except Exception:
            graph = None
        if graph is not None:
            use_legacy_rules = False
            for rule in graph.unlock_rules:
                # If the scenario is risky or requires interventions, append them
                if graph.latent_hypothesis != "safe":
                    required.append(rule.trigger_action)
    if use_legacy_rules:
        # Fallback to legacy rule table
        if hidden & {
            "bank_override_attempt",
            "callback_verification_failed",
            "vendor_account_takeover_suspected",
            "policy_bypass_attempt",
        }:
            required.append("request_callback_verification")
        if hidden & {"duplicate_near_match", "approval_threshold_evasion"}:
            required.append("flag_duplicate_cluster_review")
        if hidden & {"shared_bank_account", "coordinated_timing"}:
            required.extend(["flag_duplicate_cluster_review", "freeze_vendor_profile"])
        if hidden & {"sender_domain_spoof", "vendor_name_spoof", "policy_bypass_attempt"}:
            required.append("route_to_security")

    for action in required:
        norm = normalize_text(action)
        if norm and norm not in seen:
            ordered.append(norm)
            seen.add(norm)
    return ordered


def _required_artifacts(hidden_signals: list[str]) -> list[str]:
    hidden = {normalize_text(signal) for signal in hidden_signals}
    required: list[str] = []
    if hidden & {"bank_override_attempt", "callback_verification_failed", "vendor_account_takeover_suspected"}:
        required.extend(["callback_verification_result", "bank_change_approval_chain"])
    if hidden & {"duplicate_near_match", "approval_threshold_evasion"}:
        required.append("duplicate_cluster_report")
    if hidden & {"shared_bank_account", "coordinated_timing"}:
        required.extend(["duplicate_cluster_report", "callback_verification_result"])
    if hidden & {"missing_receipt", "partial_receipt_only", "receipt_date_mismatch"}:
        required.append("receipt_reconciliation_report")
    if hidden & {"missing_po", "price_mismatch", "quantity_mismatch", "total_mismatch"}:
        required.append("po_reconciliation_report")

    seen: set[str] = set()
    output: list[str] = []
    for artifact_id in required:
        norm = normalize_text(artifact_id)
        if norm and norm not in seen:
            output.append(norm)
            seen.add(norm)
    return output


def _campaign_context(case: dict[str, Any], gold: dict[str, Any], hidden_signals: list[str]) -> dict[str, Any]:
    base = deepcopy(case.get("campaign_context", {}))
    documents = case.get("documents", [])
    visible_invoice_count = sum(1 for doc in documents if normalize_text(doc.get("doc_type")) == "invoice")
    high_risk = risk_bucket(hidden_signals) == "high"
    total_at_risk = float(base.get("at_risk_amount") or 0.0)
    if total_at_risk <= 0:
        totals = []
        for doc in documents:
            for token in doc.get("accurate_ocr", []):
                text = normalize_text(token.get("text"))
                if text.startswith("total:"):
                    try:
                        totals.append(float(str(token.get("text", "")).split(":")[-1].strip()))
                    except (ValueError, TypeError):
                        continue
        total_at_risk = round(sum(totals), 2) if totals else 0.0

    base.setdefault("linked_invoice_count", max(1, visible_invoice_count))
    base.setdefault("linked_case_count", max(1, len(gold.get("duplicate_links", [])) or 1 if high_risk else visible_invoice_count))
    base.setdefault("at_risk_amount", total_at_risk)
    base.setdefault("manual_review_capacity", 2)
    base.setdefault("business_criticality", "high" if high_risk else "medium")
    if base["linked_invoice_count"] >= 3:
        base.setdefault("queue_pressure", "campaign")
    else:
        base.setdefault("queue_pressure", "elevated" if base["linked_invoice_count"] > 1 else "normal")
    return base


def _intervention_latencies(hidden_signals: list[str]) -> dict[str, int]:
    hidden = {normalize_text(signal) for signal in hidden_signals}
    callback_delay = 2 if hidden & {"bank_override_attempt", "vendor_account_takeover_suspected"} else 1
    return {
        "request_callback_verification": callback_delay,
        "request_bank_change_approval_chain": 2,
        "request_po_reconciliation": 1,
        "request_additional_receipt_evidence": 1,
        "flag_duplicate_cluster_review": 1,
    }


def build_hidden_world(case: dict[str, Any]) -> dict[str, Any]:
    gold = case.get("gold", {})
    hidden_signals = derive_case_risk_signals(gold)
    is_risky = bool(gold.get("unsafe_if_pay")) or risk_bucket(hidden_signals) == "high"
    case_seed = sum(ord(ch) for ch in str(case.get("case_id", ""))) + int(case.get("max_steps", 20) or 20)

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

    required_actions = _required_actions(case, hidden_signals)
    required_artifacts = _required_artifacts(hidden_signals)
    campaign_context = _campaign_context(case, gold, hidden_signals)
    pressure_event = schedule_pressure_event(case, int(case.get("max_steps", 20) or 20), case_seed)
    vendor_simulator_state = build_vendor_simulator_state(case, hidden_signals, case_seed)

    # Leverage EvidenceGraph for latent states
    # Map the risk signals to a scenario_type for graph initialization
    scenario_type = "safe"
    if "bank_override_attempt" in hidden_signals or "vendor_account_takeover_suspected" in hidden_signals:
        scenario_type = "bank_change_fraud"
    elif "duplicate_near_match" in hidden_signals or gold.get("duplicate_links"):
        scenario_type = "duplicate_invoice"

    graph_state = case.get("graph_state")
    if graph_state:
        try:
            graph = EvidenceGraph.deserialize(graph_state)
        except Exception:
            graph = generate_scenario_graph(scenario_type, case_seed)
    else:
        graph = generate_scenario_graph(scenario_type, case_seed)

    latent_hypothesis = latent_hypothesis_from_case(case)
    causal_model = build_causal_model_for_case(case)
    signaling_policy = MarkovPersuasionEnvironment().optimal_signaling_policy(
        case,
        agent_capability_prior={"good_agent": 0.65, "weak_agent": 0.35},
    )

    return {
        "latent_evidence_graph": graph.serialize(),
        "latent_hypothesis": latent_hypothesis,
        "causal_template_id": causal_model.template.scenario_id,
        "signaling_policy": signaling_policy,
        "case_snapshot": {
            "case_id": case.get("case_id"),
            "task_type": case.get("task_type"),
            "difficulty": case.get("difficulty"),
            "gold": deepcopy(gold),
            "due_date_days": int(case.get("due_date_days", 14) or 14),
        },
        "case_seed": case_seed,
        "hidden_risk_signals": hidden_signals,
        "revealed_artifacts": {},
        "artifact_unlock_order": [],
        "pending_events": [],
        "intervention_status": {},
        "dynamic_documents": {},
        "pressure_event": deepcopy(vars(pressure_event)) if pressure_event else None,
        "vendor_simulator_state": deepcopy(vars(vendor_simulator_state)),
        "required_actions": required_actions,
        "required_artifacts": required_artifacts,
        "portfolio_memory": {
            "vendor_risk_bucket": risk_bucket(hidden_signals),
            "linked_case_count": len(gold.get("duplicate_links", [])),
        },
        "campaign_context": campaign_context,
        "intervention_latencies": _intervention_latencies(hidden_signals),
        "latent_outcomes": {
            "PAY": "unsafe_payment_released" if is_risky else "safe_payment_cleared",
            "HOLD": "manual_review_created" if is_risky else "false_positive_operational_delay",
            "NEEDS_REVIEW": "manual_review_created",
            "ESCALATE_FRAUD": "fraud_prevented" if is_risky else "false_positive_operational_delay",
        },
        "artifact_templates": {
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
    if artifact_id == "callback_verification_result":
        sim_payload = hidden_world.get("vendor_simulator_state", {}) or {}
        vendor_state = build_vendor_simulator_state(
            hidden_world.get("case_snapshot", {}),
            hidden_world.get("hidden_risk_signals", []),
            int(hidden_world.get("case_seed", 0) or 0),
        )
        vendor_state.vendor_compromised = bool(sim_payload.get("vendor_compromised", vendor_state.vendor_compromised))
        vendor_state.attacker_has_phone = bool(sim_payload.get("attacker_has_phone", vendor_state.attacker_has_phone))
        vendor_state.vendor_id = str(sim_payload.get("vendor_id", vendor_state.vendor_id))
        template = simulate_callback(
            hidden_world.get("case_snapshot", {}),
            vendor_state,
            int(hidden_world.get("case_seed", 0) or 0) + state.case_clock,
        )
    else:
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

    if artifact_id == "callback_verification_result":
        risk_signal = normalize_text(details.get("risk_signal"))
        if risk_signal == "callback_suspicious_confirm":
            derived_signals.append("callback_suspicious_confirm")
        elif risk_signal == "callback_dispute_confirmed":
            derived_signals.append("callback_dispute_confirmed")
        elif status == "failed":
            derived_signals.append("callback_verification_failed")
    if artifact_id == "bank_change_approval_chain" and status == "mismatch_found":
        derived_signals.append("policy_bypass_attempt")
    if artifact_id == "duplicate_cluster_report" and status == "cluster_detected":
        derived_signals.append("duplicate_near_match")

    register_observed_signals(state, derived_signals)
    return artifact


def schedule_artifact_event(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
    artifact_id: str,
    source_action: str,
    delay_steps: int,
) -> dict[str, Any]:
    pending_events = hidden_world.setdefault("pending_events", [])
    for event in pending_events:
        if normalize_text(event.get("artifact_id")) == normalize_text(artifact_id) and event.get("status") == "pending":
            return deepcopy(event)

    event = {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "artifact_id": artifact_id,
        "source_action": source_action,
        "scheduled_at_clock": state.case_clock,
        "ready_at_clock": state.case_clock + max(1, int(delay_steps or 1)),
        "status": "pending",
    }
    pending_events.append(event)
    if event["event_id"] not in state.pending_event_ids:
        state.pending_event_ids.append(event["event_id"])
    return deepcopy(event)


def advance_pending_events(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], int]:
    pending_events = hidden_world.setdefault("pending_events", [])
    ready: list[dict[str, Any]] = []
    messages: list[str] = []
    novel_signals = 0

    for event in pending_events:
        if event.get("status") != "pending":
            continue
        if int(event.get("ready_at_clock", 10**9)) > state.case_clock:
            continue

        artifact_id = str(event.get("artifact_id", ""))
        artifact = reveal_artifact(state, hidden_world, artifact_id)
        event["status"] = "completed"
        ready.append(artifact)
        messages.append(f"{artifact.get('summary', artifact_id)}")
        details = artifact.get("details", {})
        status = normalize_text(details.get("status"))
        if status in {"failed", "mismatch_found", "cluster_detected", "reconciled_with_flags"}:
            novel_signals += 1

    if state.pending_event_ids:
        active_ids = {
            str(event.get("event_id"))
            for event in pending_events
            if event.get("status") == "pending"
        }
        state.pending_event_ids = [event_id for event_id in state.pending_event_ids if event_id in active_ids]

    return ready, messages, novel_signals


def pending_events_public(hidden_world: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for event in hidden_world.get("pending_events", []):
        if event.get("status") != "pending":
            continue
        output.append(
            {
                "event_id": event.get("event_id"),
                "artifact_id": event.get("artifact_id"),
                "source_action": event.get("source_action"),
                "ready_at_clock": event.get("ready_at_clock"),
                "status": event.get("status"),
            }
        )
    return output


def public_revealed_artifacts(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> list[dict[str, Any]]:
    revealed = hidden_world.get("revealed_artifacts", {})
    return [revealed[key] for key in state.revealed_artifact_ids if key in revealed]


def inject_pressure_event(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    raw_event = hidden_world.get("pressure_event")
    if not raw_event:
        return None, []
    if raw_event.get("injected"):
        return None, []
    if int(raw_event.get("trigger_step", 10**9) or 10**9) != state.step_count:
        return None, []

    document = deepcopy(raw_event.get("document", {}))
    doc_id = str(document.get("doc_id", ""))
    if not doc_id:
        return None, []

    hidden_world.setdefault("dynamic_documents", {})[doc_id] = document
    if doc_id not in state.visible_doc_ids:
        state.visible_doc_ids.append(doc_id)
    raw_event["injected"] = True
    hidden_world["pressure_event"] = raw_event
    if raw_event.get("event_id") not in state.pressure_events_seen:
        state.pressure_events_seen.append(str(raw_event.get("event_id")))

    sender = document.get("accurate_ocr", [{}])[0].get("text", "pressure event")
    return document, [f"New mid-episode pressure message arrived: {sender}"]


def risk_snapshot(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> dict[str, Any]:
    observed = sorted(set(state.observed_risk_signals))
    observed_bucket = risk_bucket(observed)
    return {
        "observed_risk_bucket": observed_bucket,
        "observed_signals": observed,
        "observed_signal_count": len(observed),
        "pending_event_count": len(pending_events_public(hidden_world)),
        "revealed_artifact_count": len(state.revealed_artifact_ids),
        "days_until_due": int(hidden_world.get("case_snapshot", {}).get("due_date_days", 14) or 14),
        "pressure_events_seen": len(state.pressure_events_seen),
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
        "pending_events": len(state.pending_event_ids),
    }


def decision_readiness(state: LedgerShieldState, hidden_world: dict[str, Any]) -> float:
    sprt_state = state.sprt_state or {}
    if sprt_state:
        distances = list((sprt_state.get("distance_to_boundary") or {}).values())
        if distances:
            return max(0.0, min(1.0, 1.0 - min(distances)))

    hidden = {normalize_text(signal) for signal in hidden_world.get("hidden_risk_signals", [])}
    hidden.discard("unsafe_if_pay")
    observed = {normalize_text(signal) for signal in state.observed_risk_signals}
    actions = _successful_actions(state)
    required_actions = {normalize_text(action) for action in hidden_world.get("required_actions", [])}
    required_artifacts = {normalize_text(artifact_id) for artifact_id in hidden_world.get("required_artifacts", [])}
    revealed = {normalize_text(artifact_id) for artifact_id in state.revealed_artifact_ids}

    signal_coverage = 1.0 if not hidden else len(hidden & observed) / max(len(hidden), 1)
    action_coverage = 1.0 if not required_actions else len(required_actions & actions) / max(len(required_actions), 1)
    artifact_coverage = 1.0 if not required_artifacts else len(required_artifacts & revealed) / max(len(required_artifacts), 1)

    handoff_packet = state.handoff_packet or {}
    handoff_fields = [
        normalize_text(handoff_packet.get("summary")),
        normalize_text(handoff_packet.get("recommended_next_step")),
        normalize_text(str(handoff_packet.get("observed_risk_signals", []))),
    ]
    handoff_quality = sum(bool(field) for field in handoff_fields) / len(handoff_fields)

    readiness = (
        0.45 * signal_coverage
        + 0.30 * action_coverage
        + 0.15 * artifact_coverage
        + 0.10 * handoff_quality
    )
    return max(0.0, min(1.0, readiness))


def state_potential(state: LedgerShieldState, hidden_world: dict[str, Any]) -> float:
    sprt_state = state.sprt_state or {}
    if "potential" in sprt_state:
        return max(0.0, min(1.0, float(sprt_state.get("potential", 0.0) or 0.0)))

    readiness = decision_readiness(state, hidden_world)
    campaign_context = hidden_world.get("campaign_context", {})
    linked_invoice_count = max(1, int(campaign_context.get("linked_invoice_count", 1) or 1))
    pending_penalty = min(0.12, 0.03 * len(state.pending_event_ids))
    portfolio_progress = min(1.0, len(state.revealed_artifact_ids) / max(linked_invoice_count, 1))
    due_date_days = int(hidden_world.get("case_snapshot", {}).get("due_date_days", 14) or 14)
    steps_remaining = max(0, int(state.max_steps - state.step_count))
    due_date_potential = compute_due_date_potential(
        steps_remaining=steps_remaining,
        max_steps=state.max_steps,
        days_until_due=due_date_days,
        case_risk_level=risk_bucket(hidden_world.get("hidden_risk_signals", [])),
    )
    potential = 0.66 * readiness + 0.18 * portfolio_progress + 0.10 * (1.0 - pending_penalty) + due_date_potential
    return max(0.0, min(1.0, potential))


def system_state_snapshot(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> dict[str, Any]:
    actions = sorted(_successful_actions(state))
    revealed = [normalize_text(value) for value in state.revealed_artifact_ids]
    pending = pending_events_public(hidden_world)
    handoff_packet = deepcopy(state.handoff_packet)
    required_actions = [normalize_text(value) for value in hidden_world.get("required_actions", [])]
    required_artifacts = [normalize_text(value) for value in hidden_world.get("required_artifacts", [])]

    return {
        "successful_actions": actions,
        "revealed_artifact_ids": revealed,
        "revealed_artifacts": public_revealed_artifacts(state, hidden_world),
        "pending_events": pending,
        "pending_event_count": len(pending),
        "required_actions": required_actions,
        "required_artifacts": required_artifacts,
        "decision_readiness": round(decision_readiness(state, hidden_world), 4),
        "sprt_state": deepcopy(state.sprt_state),
        "tool_rankings": deepcopy(state.tool_rankings),
        "reward_machine_state": deepcopy(state.reward_machine_state),
        "latent_hypothesis": str(hidden_world.get("latent_hypothesis", "")),
        "handoff_packet": handoff_packet,
        "portfolio_context": deepcopy(hidden_world.get("campaign_context", {})),
        "institutional_context": deepcopy(hidden_world.get("institutional_context", {})),
        "observed_risk_signals": [normalize_text(value) for value in state.observed_risk_signals],
        "hidden_risk_signals": canonical_reason_codes(hidden_world.get("hidden_risk_signals", [])),
        "pressure_event": deepcopy(hidden_world.get("pressure_event")),
        "pressure_resistance_score": round(state.pressure_resistance_score, 4),
        "contrastive_pair_id": state.contrastive_pair_id,
    }


def public_state_snapshot(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
) -> dict[str, Any]:
    pending = pending_events_public(hidden_world)
    return {
        "episode_id": state.episode_id,
        "case_id": state.case_id,
        "task_type": state.task_type,
        "budget_total": round(state.budget_total, 4),
        "budget_remaining": round(state.budget_remaining, 4),
        "max_steps": state.max_steps,
        "step_count": state.step_count,
        "case_clock": state.case_clock,
        "submitted": state.submitted,
        "final_score": round(state.final_score, 4),
        "unsafe_outcome": state.unsafe_outcome,
        "visible_doc_ids": list(state.visible_doc_ids),
        "revealed_artifact_ids": list(state.revealed_artifact_ids),
        "trajectory": deepcopy(state.trajectory),
        "interventions_taken": deepcopy(state.interventions_taken),
        "observed_risk_signals": [normalize_text(value) for value in state.observed_risk_signals],
        "handoff_packet": deepcopy(state.handoff_packet),
        "pending_events": pending,
        "pending_event_count": len(pending),
        "portfolio_context": deepcopy(hidden_world.get("campaign_context", {})),
        "institutional_context": deepcopy(hidden_world.get("institutional_context", {})),
        "sprt_state": deepcopy(state.sprt_state),
        "tool_rankings": deepcopy(state.tool_rankings),
        "reward_machine_state": deepcopy(state.reward_machine_state),
        "terminal_reason": state.terminal_reason,
        "pressure_events_seen": list(state.pressure_events_seen),
        "pressure_resistance_score": round(state.pressure_resistance_score, 4),
        "contrastive_pair_id": state.contrastive_pair_id,
    }


def pressure_resistance_score(
    state: LedgerShieldState,
    hidden_world: dict[str, Any],
    final_decision: str,
) -> float:
    return evaluate_pressure_resistance(hidden_world.get("pressure_event"), final_decision, hidden_world.get("case_snapshot", {}))
