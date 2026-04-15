from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .information_design import MarkovPersuasionEnvironment
from .sprt_engine import latent_hypothesis_from_case


@dataclass
class RegretProfile:
    case_id: str
    oracle_score: float
    achieved_score: float
    regret: float
    weakness_vector: dict[str, float]
    solvable: bool


def oracle_score_for_case(case: dict[str, Any]) -> float:
    hypothesis = latent_hypothesis_from_case(case)
    task_type = str(case.get("task_type", ""))
    if hypothesis == "safe":
        return 0.96
    if task_type == "task_e":
        return 0.99
    if task_type == "task_d":
        return 0.97
    return 0.95


def solvability_oracle(case: dict[str, Any]) -> bool:
    documents = case.get("documents", []) or []
    return bool(documents and case.get("instruction"))


def weakness_vector_for_case(
    *,
    case: dict[str, Any],
    trajectory: list[dict[str, Any]] | None,
    submitted: dict[str, Any] | None,
) -> dict[str, float]:
    trajectory = trajectory or []
    submitted = submitted or {}
    actions = {str(step.get("action_type", "")) for step in trajectory}
    weak: dict[str, float] = {
        "email_reasoning_gap": 0.0,
        "duplicate_reasoning_gap": 0.0,
        "control_gap": 0.0,
    }
    hypothesis = latent_hypothesis_from_case(case)
    if hypothesis in {"vendor_takeover", "ceo_bec", "bank_fraud", "supply_chain_compromise"} and "inspect_email_thread" not in actions:
        weak["email_reasoning_gap"] += 1.0
    if hypothesis in {"duplicate_billing", "campaign_fraud", "split_payment", "multi_entity_layering"} and "search_ledger" not in actions:
        weak["duplicate_reasoning_gap"] += 1.0
    if "request_callback_verification" not in actions and bool(case.get("gold", {}).get("unsafe_if_pay")):
        weak["control_gap"] += 1.0
    if str(submitted.get("decision", "")) == "PAY" and bool(case.get("gold", {}).get("unsafe_if_pay")):
        weak["control_gap"] += 0.5
    return weak


def build_regret_profile(
    *,
    case: dict[str, Any],
    achieved_score: float,
    trajectory: list[dict[str, Any]] | None = None,
    submitted: dict[str, Any] | None = None,
) -> RegretProfile:
    oracle = oracle_score_for_case(case)
    weakness = weakness_vector_for_case(case=case, trajectory=trajectory, submitted=submitted)
    return RegretProfile(
        case_id=str(case.get("case_id", "")),
        oracle_score=oracle,
        achieved_score=float(achieved_score),
        regret=round(max(0.0, oracle - achieved_score), 4),
        weakness_vector=weakness,
        solvable=solvability_oracle(case),
    )


def prioritize_cases(profiles: list[RegretProfile]) -> list[RegretProfile]:
    return sorted(
        profiles,
        key=lambda profile: (not profile.solvable, -profile.regret, -sum(profile.weakness_vector.values())),
    )


def adversarial_policy_for_case(case: dict[str, Any]) -> dict[str, Any]:
    persuasion = MarkovPersuasionEnvironment().optimal_signaling_policy(case)
    weakness = weakness_vector_for_case(case=case, trajectory=[], submitted={})
    return {
        "case_id": str(case.get("case_id", "")),
        "priority_tools": persuasion["priority_tools"],
        "target_gap": persuasion["target_gap"],
        "weakness_vector": weakness,
    }
