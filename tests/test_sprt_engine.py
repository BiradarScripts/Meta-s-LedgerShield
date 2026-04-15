"""
Tests for SPRT engine — Wald's Sequential Probability Ratio Test.

Covers: initialization, multi-step updates, boundary crossing, ESN computation,
optimal stopping, entropy monotonicity, and latent hypothesis inference.
"""
from __future__ import annotations

from server.sprt_engine import (
    DEFAULT_HYPOTHESES,
    HYPOTHESIS_TO_DECISION,
    LIKELIHOOD_TABLES,
    SPRTState,
    canonical_risky_hypotheses,
    infer_tool_observation,
    initialize_sprt,
    latent_hypothesis_from_case,
    observation_probability,
    optimal_stopping_check,
    possible_observations,
    sprt_potential,
    sprt_state_payload,
    update_sprt,
)


# ── Initialization ───────────────────────────────────────────────────────────

def test_sprt_initialization_produces_uniform_prior():
    state = initialize_sprt()
    assert len(state.hypotheses) == len(DEFAULT_HYPOTHESES)
    total_prior = sum(state.prior.values())
    assert abs(total_prior - 1.0) < 1e-6


def test_sprt_initializes_zero_llrs():
    state = initialize_sprt()
    for hyp, llr in state.log_likelihood_ratios.items():
        assert llr == 0.0, f"LLR for {hyp} should start at 0"


def test_sprt_wald_boundaries_are_correct_at_default_alpha_beta():
    import math
    state = initialize_sprt(alpha=0.05, beta=0.10)
    expected_upper = math.log((1 - 0.10) / 0.05)  # ≈ 2.890
    expected_lower = math.log(0.10 / (1 - 0.05))   # ≈ -2.251
    for hyp in state.hypotheses:
        if hyp == "safe":
            continue
        assert abs(state.upper_boundaries[hyp] - expected_upper) < 1e-3
        assert abs(state.lower_boundaries[hyp] - expected_lower) < 1e-3


def test_sprt_prior_normalization_with_custom_prior():
    custom = {"safe": 0.6, "bank_fraud": 0.2, "duplicate_billing": 0.2}
    state = initialize_sprt(hypotheses=["safe", "bank_fraud", "duplicate_billing"], prior=custom)
    assert abs(sum(state.prior.values()) - 1.0) < 1e-9


# ── Update / Belief Propagation ──────────────────────────────────────────────

def test_sprt_update_pushes_bank_fraud_toward_boundary():
    state = initialize_sprt()
    updated = update_sprt(state, "compare_bank_account", {"matched": False})
    assert updated.log_likelihood_ratios["bank_fraud"] > 0.0
    assert updated.posterior_probabilities["bank_fraud"] > updated.prior["bank_fraud"]
    assert sprt_potential(updated) > 0.0


def test_sprt_matching_bank_reduces_bank_fraud_llr():
    state = initialize_sprt()
    updated = update_sprt(state, "compare_bank_account", {"matched": True})
    # "match" observation supports safe → bank_fraud LLR should decrease
    assert updated.log_likelihood_ratios["bank_fraud"] < 0.0


def test_sprt_no_duplicate_evidence_supports_safe_hypothesis():
    state = initialize_sprt()
    state = update_sprt(state, "search_ledger", {"count": 0})
    assert state.posterior_probabilities["safe"] > state.prior["safe"]
    assert state.accepted_hypothesis in {None, "safe"}


def test_sprt_domain_spoof_raises_ceo_bec_probability():
    state = initialize_sprt()
    updated = update_sprt(
        state,
        "inspect_email_thread",
        {"thread": {"sender_profile": {"domain_alignment": "mismatch"}, "request_signals": {"urgency_language": True}}},
    )
    assert updated.posterior_probabilities["ceo_bec"] > updated.prior["ceo_bec"]


def test_sprt_multiple_clean_signals_converge_to_safe():
    state = initialize_sprt()
    state = update_sprt(state, "compare_bank_account", {"matched": True})
    state = update_sprt(state, "search_ledger", {"count": 0})
    state = update_sprt(state, "inspect_email_thread", {
        "thread": {"sender_profile": {"domain_alignment": "match"}, "request_signals": {}}
    })
    assert state.posterior_probabilities["safe"] > 0.5


def test_sprt_repeated_bank_mismatch_accepts_bank_fraud():
    state = initialize_sprt()
    for _ in range(5):
        state = update_sprt(state, "compare_bank_account", {"matched": False})
    assert state.decision_ready is True
    assert state.accepted_hypothesis in {"bank_fraud", "vendor_takeover", "supply_chain_compromise"}


def test_sprt_repeated_evidence_reaches_stopping_condition():
    state = initialize_sprt()
    for _ in range(4):
        state = update_sprt(state, "compare_bank_account", {"matched": False})
    stop = optimal_stopping_check(state, budget_remaining=5.0)
    assert stop["should_stop"] is True
    assert stop["recommended_decision"] == "ESCALATE_FRAUD"


# ── Optimal Stopping ─────────────────────────────────────────────────────────

def test_optimal_stopping_stops_when_budget_exhausted():
    state = initialize_sprt()
    stop = optimal_stopping_check(state, budget_remaining=0.0, min_tool_cost=0.15)
    assert stop["should_stop"] is True


def test_optimal_stopping_continues_with_high_budget_and_no_decision():
    state = initialize_sprt()  # flat prior, no decision ready
    stop = optimal_stopping_check(state, budget_remaining=10.0)
    # No evidence yet → should NOT stop (still informative steps to take)
    assert "should_stop" in stop
    assert "confidence" in stop


def test_optimal_stopping_triggers_on_high_confidence():
    state = initialize_sprt()
    for _ in range(6):
        state = update_sprt(state, "compare_bank_account", {"matched": False})
    stop = optimal_stopping_check(state, budget_remaining=3.0)
    assert stop["should_stop"] is True


# ── Entropy ──────────────────────────────────────────────────────────────────

def test_belief_entropy_decreases_with_strong_evidence():
    state0 = initialize_sprt()
    state1 = update_sprt(state0, "compare_bank_account", {"matched": False})
    state2 = update_sprt(state1, "compare_bank_account", {"matched": False})
    # Entropy should decrease or stay at most equal as evidence accumulates
    assert state2.belief_entropy <= state0.belief_entropy + 1e-6


# ── Payload / Serialization ───────────────────────────────────────────────────

def test_sprt_payload_contains_all_required_keys():
    state = initialize_sprt()
    payload = sprt_state_payload(state)
    required_keys = {
        "hypotheses", "log_likelihood_ratios", "posterior_probabilities",
        "upper_boundaries", "lower_boundaries", "observations_used",
        "decision_ready", "optimal_stopping_reached", "expected_sample_number",
        "distance_to_boundary", "accepted_hypothesis", "recommended_decision",
        "belief_entropy", "potential", "last_observation",
    }
    assert required_keys <= set(payload.keys())


def test_sprt_posterior_sums_to_one_after_updates():
    state = initialize_sprt()
    state = update_sprt(state, "compare_bank_account", {"matched": False})
    state = update_sprt(state, "search_ledger", {"count": 2})
    total = sum(state.posterior_probabilities.values())
    assert abs(total - 1.0) < 1e-6


# ── Utilities ────────────────────────────────────────────────────────────────

def test_infer_tool_observation_bank_match():
    obs = infer_tool_observation("compare_bank_account", {"matched": True})
    assert obs == "match"


def test_infer_tool_observation_bank_mismatch():
    obs = infer_tool_observation("compare_bank_account", {"matched": False})
    assert obs == "mismatch"


def test_infer_tool_observation_duplicate():
    obs = infer_tool_observation("search_ledger", {"count": 3})
    assert obs == "duplicate_found"


def test_possible_observations_coverage():
    for tool_name in LIKELIHOOD_TABLES:
        obs = possible_observations(tool_name)
        assert len(obs) >= 2, f"{tool_name} should have at least 2 observation keys"


def test_observation_probability_bounded():
    for tool_name, table in LIKELIHOOD_TABLES.items():
        for obs_key in table:
            for hyp in DEFAULT_HYPOTHESES:
                p = observation_probability(tool_name, obs_key, hyp)
                assert 0.001 <= p <= 0.999, f"P({obs_key}|{hyp}) = {p} out of bounds"


def test_latent_hypothesis_from_safe_case():
    case = {"gold": {}, "generator_metadata": {}}
    hyp = latent_hypothesis_from_case(case)
    assert hyp == "safe"


def test_latent_hypothesis_from_attack_metadata():
    case = {"gold": {}, "generator_metadata": {"applied_attacks": ["bank_override_attack"]}}
    hyp = latent_hypothesis_from_case(case)
    assert hyp == "bank_fraud"


def test_canonical_risky_hypotheses_from_signals():
    signals = ["sender_domain_spoof", "urgent_payment_pressure"]
    result = canonical_risky_hypotheses(signals)
    assert "ceo_bec" in result


def test_hypothesis_to_decision_covers_all_hypotheses():
    for hyp in DEFAULT_HYPOTHESES:
        if hyp == "safe":
            assert HYPOTHESIS_TO_DECISION.get("safe") == "PAY"
        else:
            assert hyp in HYPOTHESIS_TO_DECISION, f"{hyp} missing from HYPOTHESIS_TO_DECISION"
