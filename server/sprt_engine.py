from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .risk_rules import derive_case_risk_signals
from .schema import canonical_reason_codes, normalize_text


DEFAULT_HYPOTHESES = [
    "safe",
    "bank_fraud",
    "duplicate_billing",
    "vendor_takeover",
    "ceo_bec",
    "phantom_vendor",
    "supply_chain_compromise",
    "insider_collusion",
    "multi_entity_layering",
    "campaign_fraud",
    "split_payment",
    "threshold_evasion",
]

HYPOTHESIS_TO_DECISION = {
    "safe": "PAY",
    "bank_fraud": "ESCALATE_FRAUD",
    "duplicate_billing": "HOLD",
    "vendor_takeover": "ESCALATE_FRAUD",
    "ceo_bec": "ESCALATE_FRAUD",
    "phantom_vendor": "ESCALATE_FRAUD",
    "supply_chain_compromise": "ESCALATE_FRAUD",
    "insider_collusion": "ESCALATE_FRAUD",
    "multi_entity_layering": "ESCALATE_FRAUD",
    "campaign_fraud": "ESCALATE_FRAUD",
    "split_payment": "HOLD",
    "threshold_evasion": "NEEDS_REVIEW",
}

ATTACK_NAME_TO_HYPOTHESIS = {
    "bank_override_attack": "bank_fraud",
    "vendor_takeover_attack": "vendor_takeover",
    "ceo_fraud_attack": "ceo_bec",
    "domain_typosquat_attack": "vendor_takeover",
    "near_duplicate_invoice_attack": "duplicate_billing",
    "fake_receipt_attack": "duplicate_billing",
    "phantom_vendor_attack": "phantom_vendor",
    "inflated_line_items_attack": "duplicate_billing",
    "urgency_spoof_attack": "ceo_bec",
    "approval_threshold_evasion_attack": "threshold_evasion",
    "workflow_override_attack": "insider_collusion",
    "split_payment_attack": "split_payment",
    "coordinated_campaign_attack": "campaign_fraud",
    "supply_chain_compromise_attack": "supply_chain_compromise",
    "insider_collusion_attack": "insider_collusion",
    "multi_entity_layering_attack": "multi_entity_layering",
}

LIKELIHOOD_TABLES: dict[str, dict[str, dict[str, float]]] = {
    "compare_bank_account": {
        "mismatch": {
            "safe": 0.02,
            "bank_fraud": 0.95,
            "duplicate_billing": 0.05,
            "vendor_takeover": 0.88,
            "ceo_bec": 0.72,
            "phantom_vendor": 0.60,
            "supply_chain_compromise": 0.84,
            "insider_collusion": 0.46,
            "multi_entity_layering": 0.68,
            "campaign_fraud": 0.64,
            "split_payment": 0.18,
            "threshold_evasion": 0.16,
        },
        "match": {
            "safe": 0.98,
            "bank_fraud": 0.05,
            "duplicate_billing": 0.95,
            "vendor_takeover": 0.12,
            "ceo_bec": 0.28,
            "phantom_vendor": 0.40,
            "supply_chain_compromise": 0.16,
            "insider_collusion": 0.54,
            "multi_entity_layering": 0.32,
            "campaign_fraud": 0.36,
            "split_payment": 0.82,
            "threshold_evasion": 0.84,
        },
    },
    "search_ledger": {
        "duplicate_found": {
            "safe": 0.03,
            "bank_fraud": 0.10,
            "duplicate_billing": 0.92,
            "vendor_takeover": 0.14,
            "ceo_bec": 0.08,
            "phantom_vendor": 0.06,
            "supply_chain_compromise": 0.16,
            "insider_collusion": 0.20,
            "multi_entity_layering": 0.72,
            "campaign_fraud": 0.80,
            "split_payment": 0.88,
            "threshold_evasion": 0.74,
        },
        "no_duplicate": {
            "safe": 0.97,
            "bank_fraud": 0.90,
            "duplicate_billing": 0.08,
            "vendor_takeover": 0.86,
            "ceo_bec": 0.92,
            "phantom_vendor": 0.94,
            "supply_chain_compromise": 0.84,
            "insider_collusion": 0.80,
            "multi_entity_layering": 0.28,
            "campaign_fraud": 0.20,
            "split_payment": 0.12,
            "threshold_evasion": 0.26,
        },
    },
    "inspect_email_thread": {
        "domain_spoof_detected": {
            "safe": 0.01,
            "bank_fraud": 0.78,
            "duplicate_billing": 0.05,
            "vendor_takeover": 0.92,
            "ceo_bec": 0.94,
            "phantom_vendor": 0.62,
            "supply_chain_compromise": 0.87,
            "insider_collusion": 0.55,
            "multi_entity_layering": 0.50,
            "campaign_fraud": 0.67,
            "split_payment": 0.18,
            "threshold_evasion": 0.24,
        },
        "domain_clean": {
            "safe": 0.99,
            "bank_fraud": 0.22,
            "duplicate_billing": 0.95,
            "vendor_takeover": 0.08,
            "ceo_bec": 0.06,
            "phantom_vendor": 0.38,
            "supply_chain_compromise": 0.13,
            "insider_collusion": 0.45,
            "multi_entity_layering": 0.50,
            "campaign_fraud": 0.33,
            "split_payment": 0.82,
            "threshold_evasion": 0.76,
        },
    },
    "lookup_vendor_history": {
        "suspicious_history": {
            "safe": 0.10,
            "bank_fraud": 0.74,
            "duplicate_billing": 0.18,
            "vendor_takeover": 0.70,
            "ceo_bec": 0.30,
            "phantom_vendor": 0.82,
            "supply_chain_compromise": 0.78,
            "insider_collusion": 0.60,
            "multi_entity_layering": 0.52,
            "campaign_fraud": 0.48,
            "split_payment": 0.35,
            "threshold_evasion": 0.32,
        },
        "clean_history": {
            "safe": 0.90,
            "bank_fraud": 0.26,
            "duplicate_billing": 0.82,
            "vendor_takeover": 0.30,
            "ceo_bec": 0.70,
            "phantom_vendor": 0.18,
            "supply_chain_compromise": 0.22,
            "insider_collusion": 0.40,
            "multi_entity_layering": 0.48,
            "campaign_fraud": 0.52,
            "split_payment": 0.65,
            "threshold_evasion": 0.68,
        },
    },
    "callback_verification_result": {
        "callback_dispute": {
            "safe": 0.01,
            "bank_fraud": 0.88,
            "duplicate_billing": 0.04,
            "vendor_takeover": 0.85,
            "ceo_bec": 0.36,
            "phantom_vendor": 0.66,
            "supply_chain_compromise": 0.82,
            "insider_collusion": 0.40,
            "multi_entity_layering": 0.46,
            "campaign_fraud": 0.40,
            "split_payment": 0.10,
            "threshold_evasion": 0.08,
        },
        "callback_clean": {
            "safe": 0.94,
            "bank_fraud": 0.05,
            "duplicate_billing": 0.90,
            "vendor_takeover": 0.08,
            "ceo_bec": 0.32,
            "phantom_vendor": 0.24,
            "supply_chain_compromise": 0.15,
            "insider_collusion": 0.55,
            "multi_entity_layering": 0.40,
            "campaign_fraud": 0.44,
            "split_payment": 0.78,
            "threshold_evasion": 0.82,
        },
        "callback_suspicious_confirm": {
            "safe": 0.04,
            "bank_fraud": 0.08,
            "duplicate_billing": 0.06,
            "vendor_takeover": 0.20,
            "ceo_bec": 0.34,
            "phantom_vendor": 0.12,
            "supply_chain_compromise": 0.28,
            "insider_collusion": 0.62,
            "multi_entity_layering": 0.36,
            "campaign_fraud": 0.28,
            "split_payment": 0.10,
            "threshold_evasion": 0.12,
        },
    },
    "duplicate_cluster_report": {
        "cluster_detected": {
            "safe": 0.02,
            "bank_fraud": 0.06,
            "duplicate_billing": 0.95,
            "vendor_takeover": 0.10,
            "ceo_bec": 0.04,
            "phantom_vendor": 0.06,
            "supply_chain_compromise": 0.12,
            "insider_collusion": 0.18,
            "multi_entity_layering": 0.76,
            "campaign_fraud": 0.82,
            "split_payment": 0.90,
            "threshold_evasion": 0.78,
        },
        "no_cluster": {
            "safe": 0.98,
            "bank_fraud": 0.94,
            "duplicate_billing": 0.05,
            "vendor_takeover": 0.90,
            "ceo_bec": 0.96,
            "phantom_vendor": 0.94,
            "supply_chain_compromise": 0.88,
            "insider_collusion": 0.82,
            "multi_entity_layering": 0.24,
            "campaign_fraud": 0.18,
            "split_payment": 0.10,
            "threshold_evasion": 0.22,
        },
    },
    "bank_change_approval_chain": {
        "mismatch_found": {
            "safe": 0.01,
            "bank_fraud": 0.92,
            "duplicate_billing": 0.05,
            "vendor_takeover": 0.78,
            "ceo_bec": 0.40,
            "phantom_vendor": 0.55,
            "supply_chain_compromise": 0.84,
            "insider_collusion": 0.62,
            "multi_entity_layering": 0.48,
            "campaign_fraud": 0.44,
            "split_payment": 0.08,
            "threshold_evasion": 0.06,
        },
        "chain_clean": {
            "safe": 0.99,
            "bank_fraud": 0.08,
            "duplicate_billing": 0.95,
            "vendor_takeover": 0.22,
            "ceo_bec": 0.60,
            "phantom_vendor": 0.45,
            "supply_chain_compromise": 0.16,
            "insider_collusion": 0.38,
            "multi_entity_layering": 0.52,
            "campaign_fraud": 0.56,
            "split_payment": 0.92,
            "threshold_evasion": 0.94,
        },
    },
    "po_reconciliation_report": {
        "reconciled_with_flags": {
            "safe": 0.04,
            "bank_fraud": 0.08,
            "duplicate_billing": 0.70,
            "vendor_takeover": 0.12,
            "ceo_bec": 0.10,
            "phantom_vendor": 0.74,
            "supply_chain_compromise": 0.34,
            "insider_collusion": 0.58,
            "multi_entity_layering": 0.22,
            "campaign_fraud": 0.24,
            "split_payment": 0.42,
            "threshold_evasion": 0.46,
        },
        "po_clean": {
            "safe": 0.96,
            "bank_fraud": 0.92,
            "duplicate_billing": 0.30,
            "vendor_takeover": 0.88,
            "ceo_bec": 0.90,
            "phantom_vendor": 0.26,
            "supply_chain_compromise": 0.66,
            "insider_collusion": 0.42,
            "multi_entity_layering": 0.78,
            "campaign_fraud": 0.76,
            "split_payment": 0.58,
            "threshold_evasion": 0.54,
        },
    },
    "receipt_reconciliation_report": {
        "reconciled_with_flags": {
            "safe": 0.06,
            "bank_fraud": 0.10,
            "duplicate_billing": 0.62,
            "vendor_takeover": 0.14,
            "ceo_bec": 0.10,
            "phantom_vendor": 0.70,
            "supply_chain_compromise": 0.30,
            "insider_collusion": 0.50,
            "multi_entity_layering": 0.20,
            "campaign_fraud": 0.20,
            "split_payment": 0.38,
            "threshold_evasion": 0.40,
        },
        "receipt_clean": {
            "safe": 0.94,
            "bank_fraud": 0.90,
            "duplicate_billing": 0.38,
            "vendor_takeover": 0.86,
            "ceo_bec": 0.90,
            "phantom_vendor": 0.30,
            "supply_chain_compromise": 0.70,
            "insider_collusion": 0.50,
            "multi_entity_layering": 0.80,
            "campaign_fraud": 0.80,
            "split_payment": 0.62,
            "threshold_evasion": 0.60,
        },
    },
}


@dataclass
class SPRTState:
    hypotheses: list[str]
    log_likelihood_ratios: dict[str, float]
    upper_boundaries: dict[str, float]
    lower_boundaries: dict[str, float]
    observations_used: int = 0
    decision_ready: bool = False
    optimal_stopping_reached: bool = False
    expected_sample_number: float = 0.0
    distance_to_boundary: dict[str, float] = field(default_factory=dict)
    prior: dict[str, float] = field(default_factory=dict)
    posterior_probabilities: dict[str, float] = field(default_factory=dict)
    accepted_hypothesis: str | None = None
    recommended_decision: str | None = None
    belief_entropy: float = 0.0
    last_observation: dict[str, Any] = field(default_factory=dict)


def _normalize_prior(hypotheses: list[str], prior: dict[str, float] | None) -> dict[str, float]:
    if not hypotheses:
        raise ValueError("SPRT requires at least one hypothesis.")

    if prior is None:
        base = 1.0 / len(hypotheses)
        return {hypothesis: base for hypothesis in hypotheses}

    cleaned = {hypothesis: max(0.0, float(prior.get(hypothesis, 0.0) or 0.0)) for hypothesis in hypotheses}
    total = sum(cleaned.values())
    if total <= 0:
        base = 1.0 / len(hypotheses)
        return {hypothesis: base for hypothesis in hypotheses}
    return {hypothesis: value / total for hypothesis, value in cleaned.items()}


def _posterior_from_llrs(
    hypotheses: list[str],
    prior: dict[str, float],
    llrs: dict[str, float],
) -> dict[str, float]:
    safe_mass = max(prior.get("safe", 1e-6), 1e-9)
    numerators: dict[str, float] = {"safe": safe_mass}
    for hypothesis in hypotheses:
        if hypothesis == "safe":
            continue
        numerators[hypothesis] = max(prior.get(hypothesis, 1e-9), 1e-9) * math.exp(llrs.get(hypothesis, 0.0))
    total = sum(numerators.values())
    return {hypothesis: numerators.get(hypothesis, 0.0) / total for hypothesis in hypotheses}


def _entropy(probabilities: dict[str, float]) -> float:
    entropy = 0.0
    for probability in probabilities.values():
        if probability > 0.0:
            entropy -= probability * math.log(probability)
    return entropy


def _recompute_summary(state: SPRTState) -> SPRTState:
    state.posterior_probabilities = _posterior_from_llrs(
        state.hypotheses,
        state.prior,
        state.log_likelihood_ratios,
    )

    distances: dict[str, float] = {}
    accepted: str | None = None
    accepted_score = float("-inf")
    for hypothesis in state.hypotheses:
        if hypothesis == "safe":
            distances[hypothesis] = round(1.0 - state.posterior_probabilities.get("safe", 0.0), 4)
            continue
        upper = max(state.upper_boundaries.get(hypothesis, 1.0), 1e-6)
        llr = state.log_likelihood_ratios.get(hypothesis, 0.0)
        distances[hypothesis] = round(max(0.0, (upper - llr) / upper), 4)
        if llr >= upper and llr > accepted_score:
            accepted = hypothesis
            accepted_score = llr

    rejected_all = all(
        state.log_likelihood_ratios.get(hypothesis, 0.0) <= state.lower_boundaries.get(hypothesis, -math.inf)
        for hypothesis in state.hypotheses
        if hypothesis != "safe"
    )

    if accepted is None and rejected_all:
        accepted = "safe"

    state.distance_to_boundary = distances
    state.accepted_hypothesis = accepted
    state.recommended_decision = HYPOTHESIS_TO_DECISION.get(
        accepted or max(state.posterior_probabilities, key=state.posterior_probabilities.get),
        "NEEDS_REVIEW",
    )
    state.decision_ready = accepted is not None

    average_gap = 0.0
    active = 0
    for hypothesis in state.hypotheses:
        if hypothesis == "safe":
            continue
        active += 1
        average_gap += max(0.0, state.upper_boundaries[hypothesis] - state.log_likelihood_ratios[hypothesis])
    average_gap = average_gap / max(active, 1)
    state.expected_sample_number = round(max(0.0, average_gap / 0.45), 4)
    state.belief_entropy = round(_entropy(state.posterior_probabilities), 6)
    return state


def initialize_sprt(
    hypotheses: list[str] | None = None,
    alpha: float = 0.05,
    beta: float = 0.10,
    prior: dict[str, float] | None = None,
) -> SPRTState:
    hypotheses = list(hypotheses or DEFAULT_HYPOTHESES)
    if "safe" not in hypotheses:
        hypotheses.insert(0, "safe")

    prior_distribution = _normalize_prior(hypotheses, prior)
    upper = math.log((1.0 - beta) / max(alpha, 1e-9))
    lower = math.log(max(beta, 1e-9) / (1.0 - alpha))

    state = SPRTState(
        hypotheses=hypotheses,
        log_likelihood_ratios={hypothesis: 0.0 for hypothesis in hypotheses if hypothesis != "safe"},
        upper_boundaries={hypothesis: upper for hypothesis in hypotheses if hypothesis != "safe"},
        lower_boundaries={hypothesis: lower for hypothesis in hypotheses if hypothesis != "safe"},
        prior=prior_distribution,
    )
    return _recompute_summary(state)


def latent_hypothesis_from_case(case: dict[str, Any]) -> str:
    metadata = case.get("generator_metadata", {}) or {}
    attacks = metadata.get("applied_attacks", []) or []
    for attack in attacks:
        mapped = ATTACK_NAME_TO_HYPOTHESIS.get(str(attack))
        if mapped:
            return mapped

    signals = set(derive_case_risk_signals(case.get("gold", {}) or {}))
    signals.discard("unsafe_if_pay")

    if not signals:
        return "safe"
    if {"shared_bank_account", "coordinated_timing", "vendor_account_takeover_suspected"} <= signals:
        return "multi_entity_layering"
    if {"shared_bank_account", "coordinated_timing"} & signals:
        return "campaign_fraud"
    if {"vendor_account_takeover_suspected", "bank_override_attempt"} <= signals:
        return "supply_chain_compromise"
    if {"policy_bypass_attempt", "approval_threshold_evasion"} <= signals:
        return "insider_collusion"
    if {"urgent_payment_pressure", "sender_domain_spoof"} & signals:
        return "ceo_bec"
    if {"sender_domain_spoof", "vendor_account_takeover_suspected"} & signals:
        return "vendor_takeover"
    if {"duplicate_near_match", "approval_threshold_evasion"} <= signals:
        return "split_payment"
    if "approval_threshold_evasion" in signals:
        return "threshold_evasion"
    if "duplicate_near_match" in signals:
        return "duplicate_billing"
    if "bank_override_attempt" in signals:
        return "bank_fraud"
    return "safe"


def infer_tool_observation(tool_name: str, observation: dict[str, Any]) -> str | None:
    tool = normalize_text(tool_name)
    if tool == "compare_bank_account":
        return "match" if bool(observation.get("matched")) else "mismatch"
    if tool == "search_ledger":
        return "duplicate_found" if int(observation.get("count", 0) or 0) > 0 else "no_duplicate"
    if tool == "inspect_email_thread":
        thread = observation.get("thread", {}) or {}
        sender_profile = thread.get("sender_profile", {}) or {}
        request_signals = thread.get("request_signals", {}) or {}
        suspicious = (
            normalize_text(sender_profile.get("domain_alignment")) == "mismatch"
            or bool(request_signals.get("callback_discouraged"))
            or bool(request_signals.get("policy_override_language"))
            or bool(request_signals.get("urgency_language"))
        )
        return "domain_spoof_detected" if suspicious else "domain_clean"
    if tool == "lookup_vendor_history":
        suspicious_flags = observation.get("derived_flags", []) or []
        return "suspicious_history" if suspicious_flags or observation.get("history") else "clean_history"
    if tool == "callback_verification_result":
        details = observation.get("details", {}) or {}
        risk_signal = normalize_text(details.get("risk_signal") or details.get("outcome"))
        if risk_signal in {"callback_dispute_confirmed", "dispute", "callback_dispute"}:
            return "callback_dispute"
        if risk_signal in {"callback_suspicious_confirm", "adversarial_confirm"}:
            return "callback_suspicious_confirm"
        return "callback_clean"
    if tool == "duplicate_cluster_report":
        details = observation.get("details", {}) or {}
        return "cluster_detected" if normalize_text(details.get("status")) == "cluster_detected" else "no_cluster"
    if tool == "bank_change_approval_chain":
        details = observation.get("details", {}) or {}
        return "mismatch_found" if normalize_text(details.get("status")) == "mismatch_found" else "chain_clean"
    if tool == "po_reconciliation_report":
        details = observation.get("details", {}) or {}
        return "reconciled_with_flags" if normalize_text(details.get("status")) == "reconciled_with_flags" else "po_clean"
    if tool == "receipt_reconciliation_report":
        details = observation.get("details", {}) or {}
        return "reconciled_with_flags" if normalize_text(details.get("status")) == "reconciled_with_flags" else "receipt_clean"
    return None


def possible_observations(tool_name: str) -> list[str]:
    return list(LIKELIHOOD_TABLES.get(normalize_text(tool_name), {}).keys())


def observation_probability(tool_name: str, observation_key: str, hypothesis: str) -> float:
    table = LIKELIHOOD_TABLES.get(normalize_text(tool_name), {})
    observation_row = table.get(observation_key, {})
    probability = float(observation_row.get(hypothesis, 0.5) or 0.5)
    return min(0.999, max(0.001, probability))


def update_sprt(
    state: SPRTState,
    tool_name: str,
    observation: dict[str, Any],
    likelihood_model: dict[str, dict[str, dict[str, float]]] | None = None,
) -> SPRTState:
    model = likelihood_model or LIKELIHOOD_TABLES
    observation_key = observation.get("observation_key") if isinstance(observation, dict) else None
    if not observation_key:
        observation_key = infer_tool_observation(tool_name, observation)
    table = model.get(normalize_text(tool_name), {})

    state.observations_used += 1
    state.last_observation = {
        "tool_name": tool_name,
        "observation_key": observation_key,
    }

    if not table or observation_key is None or observation_key not in table:
        return _recompute_summary(state)

    for hypothesis in state.hypotheses:
        if hypothesis == "safe":
            continue
        numerator = observation_probability(tool_name, observation_key, hypothesis)
        denominator = observation_probability(tool_name, observation_key, "safe")
        state.log_likelihood_ratios[hypothesis] += math.log(numerator / denominator)
        state.log_likelihood_ratios[hypothesis] = round(state.log_likelihood_ratios[hypothesis], 6)

    return _recompute_summary(state)


def sprt_potential(state: SPRTState) -> float:
    ratios = []
    for hypothesis, llr in state.log_likelihood_ratios.items():
        upper = max(state.upper_boundaries.get(hypothesis, 1.0), 1e-6)
        ratios.append(max(0.0, min(1.0, llr / upper)))
    if not ratios:
        return 0.0
    return round(max(ratios), 4)


def optimal_stopping_check(
    state: SPRTState,
    budget_remaining: float,
    *,
    max_remaining_voi: float | None = None,
    min_tool_cost: float = 0.15,
) -> dict[str, Any]:
    posterior = state.posterior_probabilities
    best_hypothesis = max(posterior, key=posterior.get)
    best_confidence = posterior[best_hypothesis]
    should_stop = False

    if state.decision_ready:
        should_stop = True
    elif budget_remaining <= min_tool_cost:
        should_stop = True
    elif max_remaining_voi is not None and max_remaining_voi < min_tool_cost:
        should_stop = True
    elif best_confidence >= 0.86 and state.expected_sample_number > budget_remaining / max(min_tool_cost, 1e-6):
        should_stop = True

    recommendation = state.accepted_hypothesis or best_hypothesis
    decision = HYPOTHESIS_TO_DECISION.get(recommendation, "NEEDS_REVIEW")
    evidence_sufficiency = 1.0 - min(1.0, min(state.distance_to_boundary.values() or [1.0]))

    state.optimal_stopping_reached = should_stop
    return {
        "should_stop": should_stop,
        "recommended_hypothesis": recommendation,
        "recommended_decision": decision,
        "confidence": round(best_confidence, 4),
        "evidence_sufficiency": round(evidence_sufficiency, 4),
    }


def sprt_state_payload(state: SPRTState) -> dict[str, Any]:
    return {
        "hypotheses": list(state.hypotheses),
        "log_likelihood_ratios": {
            hypothesis: round(value, 4) for hypothesis, value in state.log_likelihood_ratios.items()
        },
        "posterior_probabilities": {
            hypothesis: round(value, 4) for hypothesis, value in state.posterior_probabilities.items()
        },
        "upper_boundaries": {
            hypothesis: round(value, 4) for hypothesis, value in state.upper_boundaries.items()
        },
        "lower_boundaries": {
            hypothesis: round(value, 4) for hypothesis, value in state.lower_boundaries.items()
        },
        "observations_used": state.observations_used,
        "decision_ready": state.decision_ready,
        "optimal_stopping_reached": state.optimal_stopping_reached,
        "expected_sample_number": round(state.expected_sample_number, 4),
        "distance_to_boundary": dict(state.distance_to_boundary),
        "accepted_hypothesis": state.accepted_hypothesis,
        "recommended_decision": state.recommended_decision,
        "belief_entropy": round(state.belief_entropy, 6),
        "potential": sprt_potential(state),
        "last_observation": dict(state.last_observation),
    }


def canonical_risky_hypotheses(values: list[Any]) -> list[str]:
    reasons = set(canonical_reason_codes(values))
    hypotheses: list[str] = []
    if {"shared_bank_account", "coordinated_timing", "vendor_account_takeover_suspected"} <= reasons:
        hypotheses.append("multi_entity_layering")
    if {"shared_bank_account", "coordinated_timing"} & reasons:
        hypotheses.append("campaign_fraud")
    if {"vendor_account_takeover_suspected", "bank_override_attempt"} <= reasons:
        hypotheses.append("supply_chain_compromise")
    if {"policy_bypass_attempt", "approval_threshold_evasion"} <= reasons:
        hypotheses.append("insider_collusion")
    if {"urgent_payment_pressure", "sender_domain_spoof"} & reasons:
        hypotheses.append("ceo_bec")
    if {"sender_domain_spoof", "vendor_account_takeover_suspected"} & reasons:
        hypotheses.append("vendor_takeover")
    if {"duplicate_near_match", "approval_threshold_evasion"} <= reasons:
        hypotheses.append("split_payment")
    if "approval_threshold_evasion" in reasons:
        hypotheses.append("threshold_evasion")
    if "duplicate_near_match" in reasons:
        hypotheses.append("duplicate_billing")
    if "bank_override_attempt" in reasons:
        hypotheses.append("bank_fraud")
    return list(dict.fromkeys(hypotheses))
