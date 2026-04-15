from __future__ import annotations

from copy import deepcopy
from typing import Any

from .sprt_engine import HYPOTHESIS_TO_DECISION, LIKELIHOOD_TABLES, SPRTState, observation_probability, possible_observations, update_sprt


DEFAULT_UTILITY_FUNCTION: dict[str, dict[str, float]] = {
    "PAY": {
        "safe": 1.0,
        "bank_fraud": -1.0,
        "duplicate_billing": -0.7,
        "vendor_takeover": -1.0,
        "ceo_bec": -1.0,
        "phantom_vendor": -1.0,
        "supply_chain_compromise": -1.0,
        "insider_collusion": -0.9,
        "multi_entity_layering": -1.0,
        "campaign_fraud": -1.0,
        "split_payment": -0.8,
        "threshold_evasion": -0.6,
    },
    "HOLD": {
        "safe": 0.25,
        "bank_fraud": 0.5,
        "duplicate_billing": 0.9,
        "vendor_takeover": 0.45,
        "ceo_bec": 0.45,
        "phantom_vendor": 0.4,
        "supply_chain_compromise": 0.4,
        "insider_collusion": 0.55,
        "multi_entity_layering": 0.35,
        "campaign_fraud": 0.35,
        "split_payment": 0.85,
        "threshold_evasion": 0.8,
    },
    "NEEDS_REVIEW": {
        "safe": 0.35,
        "bank_fraud": 0.65,
        "duplicate_billing": 0.8,
        "vendor_takeover": 0.65,
        "ceo_bec": 0.6,
        "phantom_vendor": 0.55,
        "supply_chain_compromise": 0.65,
        "insider_collusion": 0.6,
        "multi_entity_layering": 0.7,
        "campaign_fraud": 0.72,
        "split_payment": 0.78,
        "threshold_evasion": 0.84,
    },
    "ESCALATE_FRAUD": {
        "safe": -0.6,
        "bank_fraud": 1.0,
        "duplicate_billing": 0.6,
        "vendor_takeover": 1.0,
        "ceo_bec": 1.0,
        "phantom_vendor": 1.0,
        "supply_chain_compromise": 1.0,
        "insider_collusion": 0.95,
        "multi_entity_layering": 1.0,
        "campaign_fraud": 1.0,
        "split_payment": 0.55,
        "threshold_evasion": 0.45,
    },
}


def _expected_decision_utility(
    probabilities: dict[str, float],
    utility_function: dict[str, dict[str, float]],
) -> tuple[str, float]:
    best_decision = "NEEDS_REVIEW"
    best_utility = float("-inf")
    for decision, utilities in utility_function.items():
        expected = 0.0
        for hypothesis, probability in probabilities.items():
            expected += probability * utilities.get(hypothesis, 0.0)
        if expected > best_utility:
            best_decision = decision
            best_utility = expected
    return best_decision, best_utility


def value_of_information(
    tool_name: str,
    sprt_state: SPRTState,
    cost: float,
    utility_function: dict[str, dict[str, float]] | None = None,
) -> float:
    utility_function = utility_function or DEFAULT_UTILITY_FUNCTION
    prior_decision, prior_utility = _expected_decision_utility(
        sprt_state.posterior_probabilities,
        utility_function,
    )
    del prior_decision

    observations = possible_observations(tool_name)
    if not observations:
        return round(-cost, 4)

    expected_post_utility = 0.0
    for observation_key in observations:
        probability_of_observation = 0.0
        for hypothesis, probability in sprt_state.posterior_probabilities.items():
            probability_of_observation += probability * observation_probability(tool_name, observation_key, hypothesis)

        updated_state = update_sprt(
            deepcopy(sprt_state),
            tool_name,
            {"tool_name": tool_name, "observation_key": observation_key},
            likelihood_model={
                tool_name: {
                    observation_key: LIKELIHOOD_TABLES[tool_name][observation_key],
                }
            },
        )
        _, post_utility = _expected_decision_utility(updated_state.posterior_probabilities, utility_function)
        expected_post_utility += probability_of_observation * post_utility

    return round(expected_post_utility - prior_utility - cost, 4)


def optimal_tool_selection(
    available_tools: list[str],
    sprt_state: SPRTState,
    budget_remaining: float,
    tool_costs: dict[str, float],
) -> dict[str, Any]:
    rankings: dict[str, dict[str, float | bool | str]] = {}
    best_tool = ""
    best_ratio = float("-inf")
    best_voi = float("-inf")

    for tool_name in available_tools:
        cost = float(tool_costs.get(tool_name, 0.0) or 0.0)
        if cost > budget_remaining:
            rankings[tool_name] = {
                "voi": -cost,
                "cost": cost,
                "voi_cost_ratio": 0.0,
                "affordable": False,
            }
            continue
        voi = value_of_information(tool_name, sprt_state, cost)
        ratio = voi / cost if cost > 0 else voi
        rankings[tool_name] = {
            "voi": voi,
            "cost": cost,
            "voi_cost_ratio": round(ratio, 4),
            "affordable": True,
        }
        if ratio > best_ratio:
            best_tool = tool_name
            best_ratio = ratio
            best_voi = voi

    should_stop = best_tool == "" or best_voi <= 0.0 or best_ratio < 1.0
    return {
        "recommended_tool": best_tool,
        "voi": round(best_voi, 4) if best_tool else 0.0,
        "cost": round(float(tool_costs.get(best_tool, 0.0) or 0.0), 4) if best_tool else 0.0,
        "voi_cost_ratio": round(best_ratio, 4) if best_tool else 0.0,
        "should_stop": should_stop,
        "rankings": rankings,
    }


def myopic_vs_nonmyopic_voi(
    sprt_state: SPRTState,
    remaining_budget: float,
    *,
    available_tools: list[str] | None = None,
    tool_costs: dict[str, float] | None = None,
    horizon: int = 3,
) -> dict[str, Any]:
    available_tools = available_tools or list(LIKELIHOOD_TABLES.keys())
    tool_costs = tool_costs or {tool_name: 0.25 for tool_name in available_tools}
    myopic = optimal_tool_selection(available_tools, sprt_state, remaining_budget, tool_costs)

    if horizon <= 1 or myopic["should_stop"]:
        return {
            "myopic": myopic,
            "nonmyopic": myopic,
            "horizon": horizon,
        }

    best_plan = myopic
    best_total = float(myopic.get("voi", 0.0))
    for tool_name in available_tools:
        cost = float(tool_costs.get(tool_name, 0.0) or 0.0)
        if cost > remaining_budget:
            continue
        immediate = value_of_information(tool_name, sprt_state, cost)
        residual_budget = remaining_budget - cost
        branch_total = immediate
        for observation_key in possible_observations(tool_name):
            updated = update_sprt(
                deepcopy(sprt_state),
                tool_name,
                {"tool_name": tool_name, "observation_key": observation_key},
                likelihood_model={
                    tool_name: {
                        observation_key: LIKELIHOOD_TABLES[tool_name][observation_key],
                    }
                },
            )
            tail = optimal_tool_selection(
                [candidate for candidate in available_tools if candidate != tool_name],
                updated,
                residual_budget,
                tool_costs,
            )
            branch_total += max(0.0, float(tail.get("voi", 0.0))) / max(len(possible_observations(tool_name)), 1)
        if branch_total > best_total:
            best_total = branch_total
            best_plan = {
                "recommended_tool": tool_name,
                "voi": round(immediate, 4),
                "cost": cost,
                "voi_cost_ratio": round(immediate / cost, 4) if cost else round(immediate, 4),
                "should_stop": False,
            }

    return {
        "myopic": myopic,
        "nonmyopic": {
            **best_plan,
            "estimated_total_voi": round(best_total, 4),
        },
        "horizon": horizon,
    }
