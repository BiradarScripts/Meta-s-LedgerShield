from __future__ import annotations

from typing import Any

from .schema import (
    bbox_iou,
    canonical_reason_codes,
    normalize_id,
    normalize_text,
    numeric_match,
    token_overlap,
)
from .trajectory_grading import (
    calibration_score,
    downstream_outcome_score,
    efficiency_score,
    intervention_score,
    investigation_score,
)


def exact_or_numeric_match(pred_value: Any, gold_value: Any) -> bool:
    if isinstance(gold_value, (int, float)):
        return numeric_match(pred_value, gold_value)
    if normalize_id(pred_value) == normalize_id(gold_value):
        return True
    return normalize_text(pred_value) == normalize_text(gold_value)


def field_score(pred: dict[str, Any], gold: dict[str, Any]) -> float:
    if not gold:
        return 1.0
    hits = 0.0
    for key, gold_value in gold.items():
        if exact_or_numeric_match(pred.get(key), gold_value):
            hits += 1.0
    return hits / max(len(gold), 1)


def _line_pair_score(pred: dict[str, Any], gold: dict[str, Any]) -> float:
    checks = [
        normalize_text(pred.get("description")) == normalize_text(gold.get("description")),
        numeric_match(pred.get("qty"), gold.get("qty")),
        numeric_match(pred.get("unit_price"), gold.get("unit_price")),
        numeric_match(pred.get("line_total"), gold.get("line_total")),
    ]
    return sum(float(x) for x in checks) / len(checks)


def line_item_score(pred_lines: list[dict[str, Any]], gold_lines: list[dict[str, Any]]) -> float:
    if not pred_lines and not gold_lines:
        return 1.0
    if not pred_lines or not gold_lines:
        return 0.0

    unmatched = list(range(len(gold_lines)))
    total = 0.0

    for pred in pred_lines:
        best_idx = None
        best_score = -1.0
        for idx in unmatched:
            score = _line_pair_score(pred, gold_lines[idx])
            if score > best_score:
                best_idx = idx
                best_score = score
        if best_idx is not None:
            unmatched.remove(best_idx)
            total += best_score

    denom = max(len(pred_lines), len(gold_lines))
    return total / denom


def list_f1(pred: list[str], gold: list[str]) -> float:
    pred_set = {normalize_text(x) for x in pred if normalize_text(x)}
    gold_set = {normalize_text(x) for x in gold if normalize_text(x)}

    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0

    true_pos = len(pred_set & gold_set)
    precision = true_pos / len(pred_set)
    recall = true_pos / len(gold_set)

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _single_evidence_score(pred_ref: dict[str, Any], gold_ref: dict[str, Any]) -> float:
    if not pred_ref or not gold_ref:
        return 0.0

    doc_match = normalize_text(pred_ref.get("doc_id")) == normalize_text(gold_ref.get("doc_id"))
    page_match = int(pred_ref.get("page", 0) or 0) == int(gold_ref.get("page", 0) or 0)
    iou = bbox_iou(pred_ref.get("bbox"), gold_ref.get("bbox"))
    tok = token_overlap(pred_ref.get("token_ids"), gold_ref.get("token_ids"))

    return 0.35 * float(doc_match) + 0.15 * float(page_match) + 0.30 * iou + 0.20 * tok


def evidence_score(pred_map: dict[str, Any], gold_map: dict[str, Any]) -> float:
    if not gold_map:
        return 1.0

    scores = []
    for key, gold_ref in gold_map.items():
        pred_ref = pred_map.get(key) if isinstance(pred_map, dict) else None
        scores.append(_single_evidence_score(pred_ref or {}, gold_ref or {}))

    return sum(scores) / max(len(scores), 1)


def policy_score(pred: dict[str, str], gold: dict[str, str]) -> float:
    if not gold:
        return 1.0

    hits = 0.0
    for key, gold_value in gold.items():
        if normalize_text(pred.get(key)) == normalize_text(gold_value):
            hits += 1.0

    return hits / max(len(gold), 1)


def decision_score(pred: str, gold: str) -> float:
    return float(normalize_text(pred) == normalize_text(gold))


def counterfactual_score(counterfactual: str) -> float:
    text = normalize_text(counterfactual)
    return 1.0 if len(text.split()) >= 6 else 0.0


def fraud_score(pred: list[str], gold: list[str]) -> float:
    base = list_f1(pred, gold)
    missed = {normalize_text(x) for x in gold} - {normalize_text(x) for x in pred}
    if missed:
        base -= 0.20 * len(missed)
    return max(0.0, base)


def duplicate_score(pred: list[str], gold: list[str]) -> float:
    return list_f1(pred, gold)


def score_submission(
    task_type: str,
    submitted: dict[str, Any],
    gold: dict[str, Any],
    budget_penalty: float = 0.0,
    trajectory: list[dict[str, Any]] | None = None,
    outcome: dict[str, Any] | None = None,
    investigation_summary: dict[str, Any] | None = None,
) -> tuple[float, dict[str, float]]:
    s_investigation = investigation_score(task_type, trajectory, gold)
    s_intervention = intervention_score(submitted, trajectory, gold, outcome)
    s_calibration = calibration_score(submitted, gold)
    s_efficiency = efficiency_score(budget_penalty, trajectory)
    s_outcome = downstream_outcome_score(outcome)

    if task_type == "task_a":
        s_fields = field_score(submitted.get("extracted_fields", {}), gold.get("fields", {}))
        s_lines = line_item_score(submitted.get("line_items", []), gold.get("line_items", []))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}))
        raw = (
            0.38 * s_fields
            + 0.25 * s_lines
            + 0.20 * s_evidence
            + 0.08 * s_investigation
            + 0.04 * s_calibration
            + 0.05 * s_efficiency
        )
        return max(0.0, min(1.0, raw)), {
            "field_score": round(s_fields, 4),
            "line_item_score": round(s_lines, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
        }

    if task_type == "task_b":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_disc = list_f1(submitted.get("discrepancies", []), gold.get("discrepancies", []))
        s_policy = policy_score(submitted.get("policy_checks", {}), gold.get("policy_checks", {}))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}))
        raw = (
            0.28 * s_decision
            + 0.18 * s_disc
            + 0.18 * s_policy
            + 0.16 * s_evidence
            + 0.08 * s_investigation
            + 0.05 * s_intervention
            + 0.03 * s_calibration
            + 0.04 * s_efficiency
        )
        return max(0.0, min(1.0, raw)), {
            "decision_score": round(s_decision, 4),
            "discrepancy_score": round(s_disc, 4),
            "policy_score": round(s_policy, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
        }

    if task_type == "task_c":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_dupes = duplicate_score(submitted.get("duplicate_links", []), gold.get("duplicate_links", []))
        s_fraud = fraud_score(submitted.get("fraud_flags", []), gold.get("fraud_flags", []))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}))
        raw = (
            0.18 * s_decision
            + 0.18 * s_dupes
            + 0.24 * s_fraud
            + 0.12 * s_evidence
            + 0.08 * s_investigation
            + 0.07 * s_intervention
            + 0.05 * s_calibration
            + 0.03 * s_efficiency
            + 0.05 * s_outcome
        )
        if normalize_text(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.55
        return max(0.0, min(1.0, raw)), {
            "decision_score": round(s_decision, 4),
            "duplicate_score": round(s_dupes, 4),
            "fraud_score": round(s_fraud, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "outcome_score": round(s_outcome, 4),
        }

    if task_type == "task_d":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_reasons = list_f1(
            canonical_reason_codes(submitted.get("reason_codes", [])),
            canonical_reason_codes(gold.get("reason_codes", [])),
        )
        s_policy = policy_score(submitted.get("policy_checks", {}), gold.get("policy_checks", {}))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}))
        s_counter = counterfactual_score(submitted.get("counterfactual", ""))
        raw = (
            0.18 * s_decision
            + 0.17 * s_reasons
            + 0.14 * s_policy
            + 0.13 * s_evidence
            + 0.06 * s_counter
            + 0.09 * s_investigation
            + 0.08 * s_intervention
            + 0.05 * s_calibration
            + 0.03 * s_efficiency
            + 0.07 * s_outcome
        )
        if normalize_text(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.65
        return max(0.0, min(1.0, raw)), {
            "decision_score": round(s_decision, 4),
            "reason_score": round(s_reasons, 4),
            "policy_score": round(s_policy, 4),
            "evidence_score": round(s_evidence, 4),
            "counterfactual_score": round(s_counter, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "outcome_score": round(s_outcome, 4),
        }

    return 0.0, {"error": 0.0}