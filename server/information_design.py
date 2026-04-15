from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .sprt_engine import LIKELIHOOD_TABLES, latent_hypothesis_from_case


def _tool_discriminative_power(tool_name: str) -> float:
    table = LIKELIHOOD_TABLES.get(tool_name, {})
    if not table:
        return 0.0
    total = 0.0
    count = 0
    for observation in table.values():
        safe_probability = observation.get("safe", 0.5)
        risky_max = max(probability for hypothesis, probability in observation.items() if hypothesis != "safe")
        total += abs(risky_max - safe_probability)
        count += 1
    return round(total / max(count, 1), 4)


@dataclass
class SignalingPolicy:
    priority_tools: list[str]
    discriminative_weights: dict[str, float]
    clarity_budget: float
    ambiguity_budget: float
    target_gap: float


class MarkovPersuasionEnvironment:
    def optimal_signaling_policy(
        self,
        case: dict[str, Any],
        agent_capability_prior: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        capability = agent_capability_prior or {"good_agent": 0.6, "weak_agent": 0.4}
        hypothesis = latent_hypothesis_from_case(case)
        weights = {tool_name: _tool_discriminative_power(tool_name) for tool_name in LIKELIHOOD_TABLES}
        ordered = sorted(weights, key=weights.get, reverse=True)

        if hypothesis == "safe":
            ordered = sorted(ordered, key=lambda tool_name: (tool_name not in {"compare_bank_account", "search_ledger"}, -weights[tool_name]))
        elif hypothesis in {"campaign_fraud", "multi_entity_layering"}:
            ordered = sorted(ordered, key=lambda tool_name: (tool_name not in {"search_ledger", "duplicate_cluster_report"}, -weights[tool_name]))
        elif hypothesis in {"bank_fraud", "vendor_takeover", "supply_chain_compromise"}:
            ordered = sorted(ordered, key=lambda tool_name: (tool_name not in {"compare_bank_account", "callback_verification_result"}, -weights[tool_name]))

        gap = max(capability.values()) - min(capability.values())
        policy = SignalingPolicy(
            priority_tools=ordered[:4],
            discriminative_weights=weights,
            clarity_budget=round(0.55 + gap * 0.25, 4),
            ambiguity_budget=round(0.45 - gap * 0.15, 4),
            target_gap=round(sum(weights[tool] for tool in ordered[:3]) / max(3, 1), 4),
        )
        return {
            "hypothesis": hypothesis,
            "priority_tools": policy.priority_tools,
            "discriminative_weights": policy.discriminative_weights,
            "clarity_budget": policy.clarity_budget,
            "ambiguity_budget": max(0.1, policy.ambiguity_budget),
            "target_gap": policy.target_gap,
        }
