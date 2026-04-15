from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .causal_model import StructuralCausalModel, build_causal_model_for_case
from .schema import canonical_reason_codes, normalize_text


def _list_f1(pred: list[str], gold: list[str]) -> float:
    pred_set = {normalize_text(value) for value in pred if normalize_text(value)}
    gold_set = {normalize_text(value) for value in gold if normalize_text(value)}
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set)
    recall = tp / len(gold_set)
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class CausalGrade:
    association_score: float
    intervention_score: float
    counterfactual_score: float
    d_separation_sufficiency_score: float
    overall_score: float
    observed_nodes: list[str]
    required_actions: list[str]


def _counterfactual_alignment(text: str, scm: StructuralCausalModel) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    clean_world = scm.counterfactual(overrides={})
    safe_world = scm.counterfactual(
        overrides={
            "sender_authenticity": "verified",
            "bank_alignment": "match",
            "approval_chain_integrity": "approved",
            "duplicate_pattern": "absent",
            "portfolio_linkage": "isolated",
            "callback_result": "clean",
        }
    )
    score = 0.0
    if normalize_text(clean_world["decision"]) in normalized:
        score += 0.4
    if normalize_text(safe_world["decision"]) in normalized:
        score += 0.2
    keywords = {
        "bank": "bank_alignment",
        "callback": "callback_result",
        "duplicate": "duplicate_pattern",
        "approval": "approval_chain_integrity",
        "sender": "sender_authenticity",
    }
    matched = 0
    for keyword in keywords:
        if keyword in normalized:
            matched += 1
    score += min(0.4, matched * 0.1)
    return min(1.0, score)


def grade_causal_consistency(
    *,
    submitted: dict[str, Any],
    gold: dict[str, Any],
    trajectory: list[dict[str, Any]] | None,
    case_context: dict[str, Any] | None,
) -> CausalGrade:
    case_context = case_context or {}
    scm = build_causal_model_for_case(case_context)
    trajectory = trajectory or []
    actions = [normalize_text(step.get("action_type")) for step in trajectory if step.get("success", True)]
    observed_nodes = scm.observed_nodes_for_actions(actions)

    gold_reasons = canonical_reason_codes(gold.get("reason_codes", []) or gold.get("fraud_flags", []) or [])
    pred_reasons = canonical_reason_codes(submitted.get("reason_codes", []) or submitted.get("fraud_flags", []) or [])

    association = (
        0.55 * float(normalize_text(submitted.get("decision")) == normalize_text(gold.get("decision")))
        + 0.45 * _list_f1(pred_reasons, gold_reasons)
    )

    required_actions = [
        action
        for action, nodes in scm.template.interventional_nodes.items()
        if set(nodes) & set(scm.template.evidence_nodes)
    ]
    if not required_actions:
        intervention = 1.0
    else:
        intervention = len(set(required_actions) & set(actions)) / len(set(required_actions))

    d_sep = scm.d_separation_sufficiency(observed_nodes)
    counter = _counterfactual_alignment(str(submitted.get("counterfactual", "")), scm)
    overall = (
        0.35 * association
        + 0.25 * intervention
        + 0.20 * d_sep
        + 0.20 * counter
    )

    return CausalGrade(
        association_score=round(association, 4),
        intervention_score=round(intervention, 4),
        counterfactual_score=round(counter, 4),
        d_separation_sufficiency_score=round(d_sep, 4),
        overall_score=round(overall, 4),
        observed_nodes=sorted(observed_nodes),
        required_actions=sorted(set(required_actions)),
    )


def causal_grade_adjustment(grade: CausalGrade, weight: float = 0.05) -> float:
    return round(weight * (grade.overall_score - 0.5), 4)
