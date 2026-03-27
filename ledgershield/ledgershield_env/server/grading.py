from __future__ import annotations
from typing import Any

def _norm(v: Any) -> str:
    return str(v).strip().lower()

def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def field_score(pred: dict[str, Any], gold: dict[str, Any]) -> float:
    if not gold:
        return 0.0
    total = len(gold)
    hit = 0.0
    for key, gold_value in gold.items():
        pred_value = pred.get(key)
        if isinstance(gold_value, (int, float)):
            if abs(_safe_float(pred_value) - float(gold_value)) <= 0.01:
                hit += 1
        elif _norm(pred_value) == _norm(gold_value):
            hit += 1
    return hit / max(total, 1)

def list_f1(pred: list[str], gold: list[str]) -> float:
    pred_set = {_norm(x) for x in pred}
    gold_set = {_norm(x) for x in gold}
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set)
    recall = tp / len(gold_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

def evidence_score(pred: dict[str, Any], gold_keys: list[str]) -> float:
    if not gold_keys:
        return 1.0
    matched = 0
    for key in gold_keys:
        if key in pred and pred[key]:
            matched += 1
    return matched / len(gold_keys)

def decision_score(pred: str, gold: str) -> float:
    return 1.0 if _norm(pred) == _norm(gold) else 0.0

def duplicate_score(pred: list[str], gold: list[str]) -> float:
    return list_f1(pred, gold)

def fraud_score(pred: list[str], gold: list[str]) -> float:
    base = list_f1(pred, gold)
    gold_set = {_norm(x) for x in gold}
    pred_set = {_norm(x) for x in pred}
    missed = gold_set - pred_set
    if missed:
        base -= 0.25 * len(missed)
    return max(base, 0.0)

def score_submission(task_type: str, submitted: dict[str, Any], gold: dict[str, Any], budget_penalty: float) -> tuple[float, dict[str, float]]:
    if task_type == "task_a":
        s_fields = field_score(submitted.get("extracted_fields", {}), gold.get("fields", {}))
        s_lines = list_f1(
            [str(x) for x in submitted.get("line_items", [])],
            [str(x) for x in gold.get("line_items", [])]
        )
        s_evidence = evidence_score(submitted.get("evidence_map", {}), list(gold.get("fields", {}).keys()))
        raw = 0.5 * s_fields + 0.3 * s_lines + 0.2 * s_evidence - budget_penalty
        return max(0.0, min(1.0, raw)), {
            "field_score": s_fields,
            "line_item_score": s_lines,
            "evidence_score": s_evidence,
        }

    if task_type == "task_b":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_disc = list_f1(submitted.get("discrepancies", []), gold.get("discrepancies", []))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("required_evidence", []))
        raw = 0.5 * s_decision + 0.3 * s_disc + 0.2 * s_evidence - budget_penalty
        return max(0.0, min(1.0, raw)), {
            "decision_score": s_decision,
            "discrepancy_score": s_disc,
            "evidence_score": s_evidence,
        }

    if task_type == "task_c":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_dupes = duplicate_score(submitted.get("duplicate_links", []), gold.get("duplicate_links", []))
        s_fraud = fraud_score(submitted.get("fraud_flags", []), gold.get("fraud_flags", []))
        raw = 0.3 * s_decision + 0.3 * s_dupes + 0.4 * s_fraud - budget_penalty
        
        if _norm(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.5
            
        return max(0.0, min(1.0, raw)), {
            "decision_score": s_decision,
            "duplicate_score": s_dupes,
            "fraud_score": s_fraud,
        }
        
    return 0.0, {"error": 0.0}