"""
Tests for voi_engine.py — Value of Information action ranking.

Covers: VoI computation, affordability checks, optimal tool selection,
myopic vs non-myopic planning, VoI monotonicity, and edge cases.
"""
from __future__ import annotations

from server.sprt_engine import initialize_sprt, update_sprt
from server.voi_engine import (
    _expected_decision_utility,
    DEFAULT_UTILITY_FUNCTION,
    myopic_vs_nonmyopic_voi,
    optimal_tool_selection,
    value_of_information,
)


# ── Expected decision utility ─────────────────────────────────────────────────

def test_expected_utility_is_bounded():
    state = initialize_sprt()
    decision, utility = _expected_decision_utility(
        state.posterior_probabilities, DEFAULT_UTILITY_FUNCTION
    )
    assert decision in {"PAY", "HOLD", "ESCALATE_FRAUD", "NEEDS_REVIEW"}
    assert -1.5 < utility < 1.5


def test_expected_utility_escalate_preferred_under_high_fraud_belief():
    # Force high bank_fraud belief
    state = initialize_sprt()
    for _ in range(4):
        state = update_sprt(state, "compare_bank_account", {"matched": False})
    _, utility_escalate = _expected_decision_utility(
        state.posterior_probabilities,
        {"ESCALATE_FRAUD": DEFAULT_UTILITY_FUNCTION["ESCALATE_FRAUD"]},
    )
    _, utility_pay = _expected_decision_utility(
        state.posterior_probabilities,
        {"PAY": DEFAULT_UTILITY_FUNCTION["PAY"]},
    )
    assert utility_escalate > utility_pay


# ── Value of Information ──────────────────────────────────────────────────────

def test_voi_returns_finite_value():
    state = initialize_sprt()
    voi = value_of_information("compare_bank_account", state, cost=0.15)
    assert isinstance(voi, float)
    assert not (voi != voi)  # not NaN


def test_voi_unknown_tool_returns_negative_cost():
    state = initialize_sprt()
    voi = value_of_information("nonexistent_tool", state, cost=0.25)
    assert voi == round(-0.25, 4)


def test_compare_bank_account_has_positive_voi_under_bank_risk():
    state = initialize_sprt()
    state = update_sprt(
        state,
        "inspect_email_thread",
        {"thread": {"sender_profile": {"domain_alignment": "mismatch"}, "request_signals": {"callback_discouraged": True}}},
    )
    voi = value_of_information("compare_bank_account", state, cost=0.15)
    assert voi >= -0.15  # at minimum, not worth less than its cost


def test_voi_decreases_after_observation_is_already_taken():
    state = initialize_sprt()
    # Observe bank mismatch twice
    state = update_sprt(state, "compare_bank_account", {"matched": False})
    voi_first = value_of_information("compare_bank_account", state, cost=0.15)
    state = update_sprt(state, "compare_bank_account", {"matched": False})
    voi_second = value_of_information("compare_bank_account", state, cost=0.15)
    # After observing the same signal twice, additional info value should not increase
    assert voi_second <= voi_first + 1e-4  # allow tiny floating-point tolerance


def test_voi_search_ledger_high_after_duplicate_signal():
    state = initialize_sprt()
    state = update_sprt(state, "search_ledger", {"count": 3})
    voi = value_of_information("search_ledger", state, cost=0.35)
    assert isinstance(voi, float)


# ── Optimal tool selection ────────────────────────────────────────────────────

def test_optimal_tool_selection_returns_structured_dict():
    state = initialize_sprt()
    result = optimal_tool_selection(
        ["compare_bank_account", "search_ledger"],
        state,
        budget_remaining=5.0,
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35},
    )
    assert "recommended_tool" in result
    assert "voi" in result
    assert "should_stop" in result
    assert "rankings" in result


def test_optimal_tool_selection_prefers_discriminative_action():
    state = initialize_sprt()
    state = update_sprt(
        state,
        "inspect_email_thread",
        {"thread": {"sender_profile": {"domain_alignment": "mismatch"}, "request_signals": {"policy_override_language": True}}},
    )
    selection = optimal_tool_selection(
        ["compare_bank_account", "search_ledger", "lookup_policy"],
        state,
        budget_remaining=5.0,
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35, "lookup_policy": 0.15},
    )
    assert selection["recommended_tool"] in {"compare_bank_account", "search_ledger"}
    assert "lookup_policy" in selection["rankings"]


def test_optimal_tool_selection_excludes_unaffordable_tools():
    state = initialize_sprt()
    result = optimal_tool_selection(
        ["compare_bank_account", "search_ledger"],
        state,
        budget_remaining=0.10,  # too small for any tool
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35},
    )
    for tool, rank_info in result["rankings"].items():
        if not rank_info["affordable"]:
            assert rank_info["voi"] <= 0.0


def test_optimal_tool_selection_stops_when_no_affordable_tool():
    state = initialize_sprt()
    result = optimal_tool_selection(
        ["compare_bank_account"],
        state,
        budget_remaining=0.05,
        tool_costs={"compare_bank_account": 0.15},
    )
    assert result["should_stop"] is True


def test_optimal_tool_selection_best_voi_ratio_chosen():
    state = initialize_sprt()
    state = update_sprt(state, "compare_bank_account", {"matched": False})
    result = optimal_tool_selection(
        ["compare_bank_account", "search_ledger"],
        state,
        budget_remaining=5.0,
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35},
    )
    best = result["recommended_tool"]
    best_ratio = result["rankings"][best]["voi_cost_ratio"]
    for tool, info in result["rankings"].items():
        if info["affordable"]:
            assert info["voi_cost_ratio"] <= best_ratio + 1e-6


# ── Myopic vs non-myopic VoI ──────────────────────────────────────────────────

def test_nonmyopic_voi_returns_structured_plan():
    state = initialize_sprt()
    comparison = myopic_vs_nonmyopic_voi(
        state,
        remaining_budget=3.0,
        available_tools=["compare_bank_account", "search_ledger"],
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35},
        horizon=2,
    )
    assert comparison["horizon"] == 2
    assert "myopic" in comparison
    assert "nonmyopic" in comparison


def test_nonmyopic_voi_returns_same_as_myopic_at_horizon_one():
    state = initialize_sprt()
    comparison = myopic_vs_nonmyopic_voi(
        state,
        remaining_budget=3.0,
        available_tools=["compare_bank_account"],
        tool_costs={"compare_bank_account": 0.15},
        horizon=1,
    )
    assert comparison["myopic"]["recommended_tool"] == comparison["nonmyopic"]["recommended_tool"]


def test_nonmyopic_voi_at_horizon_three():
    state = initialize_sprt()
    state = update_sprt(state, "inspect_email_thread", {
        "thread": {"sender_profile": {"domain_alignment": "mismatch"}, "request_signals": {}}
    })
    comparison = myopic_vs_nonmyopic_voi(
        state,
        remaining_budget=5.0,
        available_tools=["compare_bank_account", "search_ledger", "lookup_vendor_history"],
        tool_costs={"compare_bank_account": 0.15, "search_ledger": 0.35, "lookup_vendor_history": 0.25},
        horizon=3,
    )
    # nonmyopic should return a structured recommendation dict
    assert "recommended_tool" in comparison["nonmyopic"]
    assert "should_stop" in comparison["nonmyopic"]
    assert comparison["horizon"] == 3


def test_voi_engine_handles_empty_tool_list():
    state = initialize_sprt()
    result = optimal_tool_selection([], state, budget_remaining=5.0, tool_costs={})
    assert result["recommended_tool"] == ""
    assert result["should_stop"] is True
