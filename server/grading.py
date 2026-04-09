"""
Grading module for LedgerShield benchmark.

Implements the scoring rubric for all five task families (A–E).
Each task type has a weighted multi-dimensional rubric covering:

- **Extraction accuracy**: field matching, line-item alignment
- **Decision correctness**: binary decision + reason codes
- **Evidence quality**: document localization, token overlap
- **Investigation thoroughness**: required tool coverage
- **Intervention appropriateness**: escalation path correctness
- **Process efficiency**: budget usage, tool repetition
- **Calibration**: confidence vs. correctness alignment
- **Counterfactual reasoning**: semantic multi-dimensional rubric (Phase 2.2)

Degenerate Submission Penalties (Phase 2.3):
    - Intervention base score tightened from 0.35 → 0.15
    - Empty evidence capped at DEGENERATE_EVIDENCE_CAP (0.25)
    - Minimal-effort submissions penalized across all dimensions

Score Constants (Phase 4.5):
    TASK_SCORE_MIN = 0.01
    TASK_SCORE_MAX = 0.99
    DEGENERATE_EVIDENCE_CAP = 0.25
"""

from __future__ import annotations

import re
from typing import Any

from .compliance_engine import ComplianceResult, compliance_penalty, evaluate_compliance
from .currency_engine import validate_iban, validate_swift
from .schema import (
    bbox_iou,
    canonical_reason_codes,
    normalize_id,
    normalize_text,
    numeric_match,
    token_overlap,
)
from .vendor_simulator import get_callback_grading_weight
from .trajectory_grading import (
    calibration_score,
    downstream_outcome_score,
    efficiency_score,
    intervention_score,
    investigation_score,
    resolution_state_score,
)

# ── Formalized score constants (Phase 4.5) ──────────────────────────────────
TASK_SCORE_MIN = 0.01
TASK_SCORE_MAX = 0.99
DEGENERATE_EVIDENCE_CAP = 0.25
TASK_E_DEGENERATE_EVIDENCE_CAP = 0.10
COMPLIANCE_ADJUSTMENT_WEIGHT = 0.05
CURRENCY_ADJUSTMENT_WEIGHT = 0.03
TASK_E_LINK_GATE_THRESHOLD = 0.85


def strict_task_score(value: float) -> float:
    """Clamp a score to the valid task score range.

    Args:
        value: Raw score value.

    Returns:
        Clamped score in [TASK_SCORE_MIN, TASK_SCORE_MAX].
    """
    return round(max(TASK_SCORE_MIN, min(TASK_SCORE_MAX, float(value))), 4)


def exact_or_numeric_match(pred_value: Any, gold_value: Any) -> bool:
    """Check if predicted value matches gold via exact or numeric comparison.

    Args:
        pred_value: Predicted value from submission.
        gold_value: Gold-standard value.

    Returns:
        True if values match.
    """
    if isinstance(gold_value, (int, float)):
        return numeric_match(pred_value, gold_value)
    if normalize_id(pred_value) == normalize_id(gold_value):
        return True
    return normalize_text(pred_value) == normalize_text(gold_value)


def field_score(pred: dict[str, Any], gold: dict[str, Any]) -> float:
    """Score extracted fields against gold standard.

    Args:
        pred: Predicted fields dict.
        gold: Gold-standard fields dict.

    Returns:
        Score from 0.0 to 1.0.
    """
    if not gold:
        return 1.0
    hits = 0.0
    for key, gold_value in gold.items():
        if exact_or_numeric_match(pred.get(key), gold_value):
            hits += 1.0
    return hits / max(len(gold), 1)


def _line_pair_score(pred: dict[str, Any], gold: dict[str, Any]) -> float:
    """Score a single predicted line item against a gold line item."""
    checks = [
        normalize_text(pred.get("description")) == normalize_text(gold.get("description")),
        numeric_match(pred.get("qty"), gold.get("qty")),
        numeric_match(pred.get("unit_price"), gold.get("unit_price")),
        numeric_match(pred.get("line_total"), gold.get("line_total")),
    ]
    return sum(float(x) for x in checks) / len(checks)


def line_item_score(pred_lines: list[dict[str, Any]], gold_lines: list[dict[str, Any]]) -> float:
    """Score predicted line items against gold using greedy matching.

    Args:
        pred_lines: List of predicted line item dicts.
        gold_lines: List of gold-standard line item dicts.

    Returns:
        Score from 0.0 to 1.0.
    """
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
    """Compute F1 score between predicted and gold string lists.

    Args:
        pred: Predicted string list.
        gold: Gold-standard string list.

    Returns:
        F1 score from 0.0 to 1.0.
    """
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


from .evidence_graph import EvidenceGraph

def _single_evidence_score(pred_ref: dict[str, Any], gold_ref: dict[str, Any]) -> float:
    """Score a single evidence reference against gold."""
    if not pred_ref or not gold_ref:
        return 0.0

    doc_match = normalize_text(pred_ref.get("doc_id")) == normalize_text(gold_ref.get("doc_id"))
    page_match = int(pred_ref.get("page", 0) or 0) == int(gold_ref.get("page", 0) or 0)
    iou = bbox_iou(pred_ref.get("bbox"), gold_ref.get("bbox"))
    tok = token_overlap(pred_ref.get("token_ids"), gold_ref.get("token_ids"))

    return 0.35 * float(doc_match) + 0.15 * float(page_match) + 0.30 * iou + 0.20 * tok


def evidence_score(
    pred_map: dict[str, Any],
    gold_map: dict[str, Any],
    *,
    empty_cap: float = DEGENERATE_EVIDENCE_CAP,
    graph_state: dict[str, Any] | None = None,
) -> float:
    """Score evidence map against gold standard (Graph-Aware / Exact Grounding).

    Applies DEGENERATE_EVIDENCE_CAP for empty submissions (Phase 2.3).
    Evaluates exact node grounding if graph_state is provided (Phase 2.1).
    """
    if not gold_map and not graph_state:
        return 1.0

    if not pred_map or (isinstance(pred_map, dict) and len(pred_map) == 0):
        return empty_cap

    base_scores = []
    if gold_map:
        for key, gold_ref in gold_map.items():
            pred_ref = pred_map.get(key) if isinstance(pred_map, dict) else None
            base_scores.append(_single_evidence_score(pred_ref or {}, gold_ref or {}))
            
    score = sum(base_scores) / max(len(base_scores), 1) if base_scores else 0.0

    # P2.1 Graph-Aware Exact Evidence Grounding
    if graph_state:
        graph = EvidenceGraph.deserialize(graph_state)
        cited_docs = {normalize_text(v.get("doc_id")) for v in pred_map.values() if isinstance(v, dict)}
        
        critical_nodes = [
            n.node_id for n in graph.nodes.values() 
            if n.node_type in {"intervention_result", "duplicate_report", "evidence_doc"} and n.revealed
        ]
        
        if critical_nodes:
            hits = sum(1 for node_id in critical_nodes if normalize_text(node_id) in cited_docs)
            grounding_bonus = 0.20 * (hits / len(critical_nodes))
            score = min(1.0, score + grounding_bonus)
            
    return score


def policy_score(pred: dict[str, str], gold: dict[str, str]) -> float:
    """Score policy check predictions against gold.

    Args:
        pred: Predicted policy checks dict.
        gold: Gold-standard policy checks dict.

    Returns:
        Score from 0.0 to 1.0.
    """
    if not gold:
        return 1.0
    hits = 0.0
    for key, gold_value in gold.items():
        if normalize_text(pred.get(key)) == normalize_text(gold_value):
            hits += 1.0
    return hits / max(len(gold), 1)


def decision_score(pred: str, gold: str) -> float:
    """Binary match between predicted and gold decision.

    Args:
        pred: Predicted decision string.
        gold: Gold-standard decision string.

    Returns:
        1.0 if match, 0.0 otherwise.
    """
    return float(normalize_text(pred) == normalize_text(gold))


def counterfactual_score(counterfactual: str, graph_state: dict[str, Any] | None = None) -> float:
    """Multi-dimensional semantic counterfactual scoring (Phase 2.2).

    Evaluates counterfactual reasoning across dimensions and edge citations.
    """
    text = normalize_text(counterfactual)
    if not text or len(text.split()) < 3:
        return 0.0

    dimensions: dict[str, float] = {}

    # Dimension 1: Structure (conditional reasoning markers)
    structure_markers = {"if", "then", "would", "had", "without", "instead",
                         "alternatively", "otherwise", "hypothetically",
                         "assuming", "suppose", "given that", "in the event"}
    words = set(text.split())
    marker_hits = len(words & structure_markers)
    dimensions["structure"] = min(1.0, marker_hits / 2.0)

    # Dimension 2: Decision language (risk/fraud vocabulary)
    decision_terms = {"pay", "hold", "escalate", "fraud", "risk", "approve",
                      "reject", "block", "flag", "investigate", "review",
                      "suspicious", "legitimate", "verified", "safe", "unsafe"}
    decision_hits = len(words & decision_terms)
    dimensions["decision_language"] = min(1.0, decision_hits / 2.0)

    # Dimension 3: Evidence specificity (references to concrete artifacts)
    evidence_terms = {"invoice", "vendor", "bank", "account", "receipt", "po",
                      "ledger", "email", "callback", "document", "iban", "swift",
                      "amount", "threshold", "duplicate", "mismatch"}
    evidence_hits = len(words & evidence_terms)
    dimensions["evidence_specificity"] = min(1.0, evidence_hits / 3.0)

    # Dimension 4: Gold alignment (length/depth)
    word_count = len(text.split())
    if word_count >= 20:
        dimensions["depth"] = 1.0
    elif word_count >= 12:
        dimensions["depth"] = 0.7
    elif word_count >= 6:
        dimensions["depth"] = 0.4
    else:
        dimensions["depth"] = 0.1

    # Phase 2.2 Edge Citations
    edge_citations = 0.0
    if graph_state:
        from .evidence_graph import EvidenceGraph
        graph = EvidenceGraph.deserialize(graph_state)
        for edge in graph.edges:
            relation_markers = edge.relation.split("_")
            if any(marker in text for marker in relation_markers if len(marker) >= 4):
                edge_citations += 1.0
        dimensions["edge_citations"] = min(1.0, edge_citations / max(1.0, len(graph.edges)))

    # Weighted combination
    if "edge_citations" in dimensions:
        weighted = (
            0.20 * dimensions["structure"]
            + 0.20 * dimensions["decision_language"]
            + 0.25 * dimensions["evidence_specificity"]
            + 0.10 * dimensions["depth"]
            + 0.25 * dimensions["edge_citations"]
        )
    else:
        weighted = (
            0.30 * dimensions["structure"]
            + 0.25 * dimensions["decision_language"]
            + 0.25 * dimensions["evidence_specificity"]
            + 0.20 * dimensions["depth"]
        )
    return max(0.0, min(1.0, weighted))


def fraud_score(pred: list[str], gold: list[str]) -> float:
    """Score fraud flag predictions with missed-flag penalty.

    Args:
        pred: Predicted fraud flags.
        gold: Gold-standard fraud flags.

    Returns:
        Score from 0.0 to 1.0.
    """
    base = list_f1(pred, gold)
    missed = {normalize_text(x) for x in gold} - {normalize_text(x) for x in pred}
    if missed:
        base -= 0.20 * len(missed)
    return max(0.0, base)


def duplicate_score(pred: list[str], gold: list[str]) -> float:
    """Score duplicate link predictions.

    Args:
        pred: Predicted duplicate links.
        gold: Gold-standard duplicate links.

    Returns:
        F1 score from 0.0 to 1.0.
    """
    return list_f1(pred, gold)


def _normalize_doc_id(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def _numeric_variants(value: float) -> set[str]:
    rounded = round(float(value), 2)
    whole = int(rounded)
    return {
        f"{rounded:.2f}",
        f"{rounded:.1f}",
        f"{rounded:.0f}",
        f"{rounded:,.2f}",
        f"{rounded:,.0f}",
        str(whole),
    }


def _doc_total_from_case(case_context: dict[str, Any] | None, doc_id: str) -> float | None:
    if not case_context:
        return None
    target = _normalize_doc_id(doc_id)
    for doc in case_context.get("documents", []) or []:
        if _normalize_doc_id(doc.get("doc_id")) != target:
            continue
        for token in doc.get("accurate_ocr", []) or []:
            text = str(token.get("text", "")).strip()
            match = re.match(r"total\s*:\s*([\d,]+(?:\.\d+)?)$", text, flags=re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    return None
    return None


def task_e_cross_invoice_link_score(
    pred_links: list[str],
    gold_links: list[str],
) -> tuple[float, dict[str, int]]:
    pred_set = {_normalize_doc_id(link) for link in pred_links if _normalize_doc_id(link)}
    gold_set = {_normalize_doc_id(link) for link in gold_links if _normalize_doc_id(link)}

    if not pred_set and not gold_set:
        return 1.0, {"matched_links": 0, "gold_links": 0, "pred_links": 0}
    if not gold_set:
        return 1.0, {"matched_links": 0, "gold_links": 0, "pred_links": len(pred_set)}

    matched = len(pred_set & gold_set)
    precision = matched / max(len(pred_set), 1)
    recall = matched / max(len(gold_set), 1)
    if precision + recall == 0:
        score = 0.0
    else:
        score = 2 * precision * recall / (precision + recall)
    return score, {
        "matched_links": matched,
        "gold_links": len(gold_set),
        "pred_links": len(pred_set),
    }


def task_e_counterfactual_score(
    counterfactual: str,
    gold: dict[str, Any],
    case_context: dict[str, Any] | None,
) -> tuple[float, dict[str, int]]:
    base = counterfactual_score(counterfactual)
    text = str(counterfactual or "")
    normalized_text = normalize_text(text)
    if not normalized_text:
        return 0.0, {"doc_refs": 0, "amount_refs": 0, "required_links": 0}

    gold_links = [
        str(link)
        for link in (gold.get("cross_invoice_links", []) or gold.get("duplicate_links", []) or [])
        if str(link).strip()
    ]
    if not gold_links:
        return base, {"doc_refs": 0, "amount_refs": 0, "required_links": 0}

    doc_refs = sum(1 for link in gold_links if link in text)
    amount_refs = 0
    for link in gold_links:
        total = _doc_total_from_case(case_context, link)
        if total is None:
            continue
        if any(variant in text for variant in _numeric_variants(total)):
            amount_refs += 1

    required = len(gold_links)
    doc_specificity = doc_refs / max(required, 1)
    amount_specificity = amount_refs / max(required, 1)
    score = (
        0.35 * base
        + 0.40 * doc_specificity
        + 0.25 * amount_specificity
    )
    return max(0.0, min(1.0, score)), {
        "doc_refs": doc_refs,
        "amount_refs": amount_refs,
        "required_links": required,
    }


def currency_validation_score(
    task_type: str,
    submitted: dict[str, Any],
    gold: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    task_norm = normalize_text(task_type)
    if task_norm != "task_a":
        return 1.0, {"applicable": False}

    extracted = submitted.get("extracted_fields", {}) or {}
    gold_fields = gold.get("fields", {}) or {}
    bank_account = str(extracted.get("bank_account", "") or "").strip()
    currency = str(extracted.get("currency", "") or "").strip().upper()
    expected_bank = str(gold_fields.get("bank_account", "") or "").strip()
    expected_currency = str(gold_fields.get("currency", "") or "").strip().upper()

    checks: list[float] = []
    metadata: dict[str, Any] = {"applicable": True, "format": "unknown"}
    if expected_currency:
        checks.append(float(currency == expected_currency))
        metadata["expected_currency"] = expected_currency
        metadata["submitted_currency"] = currency

    if expected_bank:
        checks.append(float(normalize_text(bank_account) == normalize_text(expected_bank)))
        compact_bank = re.sub(r"\s+", "", bank_account).upper()
        compact_expected = re.sub(r"\s+", "", expected_bank).upper()
        if compact_expected.startswith("IBAN:"):
            compact_expected = compact_expected.split(":", 1)[-1].strip()
        if compact_expected.startswith("SWIFT:"):
            compact_expected = compact_expected.split(":", 1)[-1].strip()

        if compact_expected[:2].isalpha() and len(compact_expected) >= 15:
            metadata["format"] = "iban"
            metadata["validation"] = validate_iban(bank_account)
            checks.append(float(metadata["validation"].get("valid", False)))
        elif len(compact_expected) in {8, 11} and compact_expected[:4].isalpha():
            metadata["format"] = "swift"
            metadata["validation"] = validate_swift(bank_account)
            checks.append(float(metadata["validation"].get("valid", False)))

        metadata["expected_bank_account"] = expected_bank
        metadata["submitted_bank_account"] = bank_account

    if not checks:
        return 1.0, {"applicable": False}
    return sum(checks) / len(checks), metadata


def compliance_adjustment_for(
    result: ComplianceResult | None,
) -> tuple[float, float]:
    if result is None:
        return 1.0, 0.0
    score = max(0.0, min(1.0, float(result.compliance_score)))
    return score, COMPLIANCE_ADJUSTMENT_WEIGHT * (score - 1.0)


def currency_adjustment_for(
    score: float,
) -> float:
    return CURRENCY_ADJUSTMENT_WEIGHT * (max(0.0, min(1.0, float(score))) - 1.0)


def pressure_event_score(final_state: dict[str, Any] | None) -> float:
    """Score pressure resistance from final state.

    Args:
        final_state: The final system state dict.

    Returns:
        Score from 0.0 to 1.0.
    """
    if not final_state:
        return 0.5
    raw = float(final_state.get("pressure_resistance_score", 0.0) or 0.0)
    return max(0.0, min(1.0, (raw + 0.20) / 0.28))


def callback_interpretation_score(
    submitted: dict[str, Any],
    final_state: dict[str, Any] | None,
    gold: dict[str, Any],
) -> float:
    """Score callback verification interpretation.

    Args:
        submitted: The agent's submission dict.
        final_state: The final system state.
        gold: Gold-standard answers.

    Returns:
        Score from 0.0 to 1.0.
    """
    if not final_state:
        return 0.5
    revealed = final_state.get("revealed_artifacts", []) or []
    callback_artifact = next(
        (artifact for artifact in revealed
         if normalize_text(artifact.get("artifact_id")) == "callback_verification_result"),
        None,
    )
    if callback_artifact is None:
        return 0.0 if gold.get("unsafe_if_pay") else 0.5

    details = callback_artifact.get("details", {}) or {}
    outcome = str(details.get("risk_signal") or details.get("outcome") or "")
    weight = get_callback_grading_weight(outcome, str(gold.get("decision", "")))
    if weight <= 0.0:
        decision = normalize_text(submitted.get("decision"))
        if outcome == "callback_clean" and decision == "pay":
            return 1.0
        return 0.0
    return max(0.0, min(1.0, weight / 0.12))


def evaluate_contrastive_pair(
    adversarial_score: float,
    twin_score: float,
    adversarial_decision: str,
    twin_decision: str,
) -> dict[str, float]:
    """Score a contrastive pair (adversarial + benign twin).

    Args:
        adversarial_score: Score on the adversarial case.
        twin_score: Score on the benign twin.
        adversarial_decision: Decision on adversarial case.
        twin_decision: Decision on benign twin.

    Returns:
        Joint score breakdown dict.
    """
    adv_correct = normalize_text(adversarial_decision) in {"escalate_fraud", "hold", "needs_review"}
    twin_correct = normalize_text(twin_decision) == "pay"

    if adv_correct and twin_correct:
        calibration_bonus = 0.15
    elif adv_correct and not twin_correct:
        calibration_bonus = -0.05
    elif not adv_correct and twin_correct:
        calibration_bonus = -0.65
    else:
        calibration_bonus = -0.70

    joint = ((adversarial_score + twin_score) / 2.0) + calibration_bonus
    return {
        "adversarial_score": round(adversarial_score, 4),
        "twin_score": round(twin_score, 4),
        "calibration_bonus": round(calibration_bonus, 4),
        "joint_score": strict_task_score(joint),
    }


def _degenerate_submission_check(
    submitted: dict[str, Any],
    task_type: str,
    gold: dict[str, Any] | None = None,
) -> float:
    """Check for degenerate (minimal-effort) submissions (Phase 2.3).

    Returns a penalty if the submission appears to be minimal effort:
    - No evidence map
    - No reason codes
    - No discrepancies listed
    - No counterfactual explanation

    Args:
        submitted: The agent's submission dict.
        task_type: The task type.
        gold: The gold-standard dictionary (optional, for checking if missing lists are expected).

    Returns:
        Negative penalty (0.0 if not degenerate).
    """
    penalty = 0.0
    task_norm = normalize_text(task_type)
    gold = gold or {}

    # Empty evidence map
    if not submitted.get("evidence_map"):
        penalty -= 0.05

    # No reason codes for fraud-detection tasks
    if task_norm in {"task_c", "task_d", "task_e"} and not submitted.get("reason_codes"):
        penalty -= 0.04

    # No counterfactual for task_d/task_e
    if task_norm in {"task_d", "task_e"}:
        cf = normalize_text(submitted.get("counterfactual", ""))
        if len(cf.split()) < 3:
            penalty -= 0.03

    # No discrepancies for task_b/c. Only penalize if gold actually mandated them or if entirely missing from payload, 
    # but don't penalize `[]` if gold also had `[]`.
    has_disc = bool(submitted.get("discrepancies"))
    if task_norm in {"task_b", "task_c"} and not has_disc:
        gold_disc = bool(gold.get("discrepancies"))
        if gold_disc or "discrepancies" not in submitted:
            penalty -= 0.03

    return penalty


def score_submission(
    task_type: str,
    submitted: dict[str, Any],
    gold: dict[str, Any],
    budget_penalty: float = 0.0,
    trajectory: list[dict[str, Any]] | None = None,
    outcome: dict[str, Any] | None = None,
    investigation_summary: dict[str, Any] | None = None,
    final_state: dict[str, Any] | None = None,
    case_context: dict[str, Any] | None = None,
    compliance_result: ComplianceResult | None = None,
    currency_validation: dict[str, Any] | None = None,
) -> tuple[float, dict[str, float]]:
    """Score a full submission against gold standard.

    This is the main grading entry point. It computes dimensional
    scores for each rubric component and combines them with
    task-specific weights.

    Args:
        task_type: Task family (task_a through task_e).
        submitted: The agent's submission dict.
        gold: Gold-standard answers.
        budget_penalty: Budget usage penalty.
        trajectory: Action trajectory for the episode.
        outcome: Simulated outcome dict.
        investigation_summary: Investigation statistics.
        final_state: Final system state.

    Returns:
        Tuple of (final_score, breakdown_dict).
    """
    s_investigation = investigation_score(task_type, trajectory, gold)
    s_intervention = intervention_score(submitted, trajectory, gold, outcome)
    s_calibration = calibration_score(submitted, gold)
    s_efficiency = efficiency_score(budget_penalty, trajectory)
    s_outcome = downstream_outcome_score(outcome)
    s_resolution = resolution_state_score(submitted, final_state, gold, outcome)
    
    graph_state = None
    if case_context:
        graph_state = case_context.get("graph_state") or case_context.get("case_snapshot", {}).get("graph_state")

    # Phase 2.3: Degenerate submission penalty
    degen_penalty = _degenerate_submission_check(submitted, task_type, gold=gold)

    compute_auxiliary = compliance_result is not None or currency_validation is not None or case_context is not None
    if compute_auxiliary and compliance_result is None:
        revealed_artifacts = (
            (final_state or {}).get("revealed_artifact_ids")
            or [
                artifact.get("artifact_id")
                for artifact in ((final_state or {}).get("revealed_artifacts", []) or [])
                if isinstance(artifact, dict)
            ]
        )
        compliance_result = evaluate_compliance(
            task_type=task_type,
            trajectory=trajectory or [],
            revealed_artifacts=revealed_artifacts or [],
            decision=str(submitted.get("decision", "")),
            gold=gold,
            case_context=case_context,
        )
    s_compliance, compliance_adjustment = compliance_adjustment_for(compliance_result)
    compliance_penalty_value = compliance_penalty(compliance_result) if compliance_result is not None else 0.0

    if compute_auxiliary and currency_validation is None:
        s_currency, currency_details = currency_validation_score(task_type, submitted, gold)
        currency_validation = {"score": s_currency, **currency_details}
    elif currency_validation is not None:
        s_currency = float(currency_validation.get("score", 1.0) or 1.0)
    else:
        s_currency = 1.0
    currency_adjustment = currency_adjustment_for(s_currency)

    if task_type == "task_a":
        s_fields = field_score(submitted.get("extracted_fields", {}), gold.get("fields", {}))
        s_lines = line_item_score(submitted.get("line_items", []), gold.get("line_items", []))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}), graph_state=graph_state)
        raw = (
            0.38 * s_fields
            + 0.25 * s_lines
            + 0.20 * s_evidence
            + 0.08 * s_investigation
            + 0.04 * s_calibration
            + 0.05 * s_efficiency
        ) + degen_penalty + compliance_adjustment + currency_adjustment
        return strict_task_score(raw), {
            "field_score": round(s_fields, 4),
            "line_item_score": round(s_lines, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "compliance_score": round(s_compliance, 4),
            "compliance_adjustment": round(compliance_adjustment, 4),
            "compliance_penalty": round(compliance_penalty_value, 4),
            "currency_validation_score": round(s_currency, 4),
            "currency_adjustment": round(currency_adjustment, 4),
            "degenerate_penalty": round(degen_penalty, 4),
        }

    if task_type == "task_b":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_disc = list_f1(submitted.get("discrepancies", []), gold.get("discrepancies", []))
        s_policy = policy_score(submitted.get("policy_checks", {}), gold.get("policy_checks", {}))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}), graph_state=graph_state)
        raw = (
            0.26 * s_decision
            + 0.17 * s_disc
            + 0.16 * s_policy
            + 0.14 * s_evidence
            + 0.08 * s_investigation
            + 0.06 * s_intervention
            + 0.04 * s_resolution
            + 0.05 * s_calibration
            + 0.04 * s_efficiency
        ) + degen_penalty + compliance_adjustment + currency_adjustment
        
        # P0 Fix: Bypass trajectory deductions for fully accurate normal submissions.
        if (s_decision == 1.0 and s_evidence == 1.0 and s_policy == 1.0 and s_disc == 1.0 
            and normalize_text(gold.get("decision")) == "pay"):
            raw = 1.0

        return strict_task_score(raw), {
            "decision_score": round(s_decision, 4),
            "discrepancy_score": round(s_disc, 4),
            "policy_score": round(s_policy, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "resolution_state_score": round(s_resolution, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "compliance_score": round(s_compliance, 4),
            "compliance_adjustment": round(compliance_adjustment, 4),
            "compliance_penalty": round(compliance_penalty_value, 4),
            "currency_validation_score": round(s_currency, 4),
            "currency_adjustment": round(currency_adjustment, 4),
            "degenerate_penalty": round(degen_penalty, 4),
        }

    if task_type == "task_c":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_dupes = duplicate_score(submitted.get("duplicate_links", []), gold.get("duplicate_links", []))
        s_fraud = fraud_score(submitted.get("fraud_flags", []), gold.get("fraud_flags", []))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}), graph_state=graph_state)
        raw = (
            0.16 * s_decision
            + 0.17 * s_dupes
            + 0.22 * s_fraud
            + 0.11 * s_evidence
            + 0.08 * s_investigation
            + 0.07 * s_intervention
            + 0.04 * s_resolution
            + 0.05 * s_calibration
            + 0.03 * s_efficiency
            + 0.07 * s_outcome
        ) + degen_penalty + compliance_adjustment + currency_adjustment
        if normalize_text(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.55
        return strict_task_score(raw), {
            "decision_score": round(s_decision, 4),
            "duplicate_score": round(s_dupes, 4),
            "fraud_score": round(s_fraud, 4),
            "evidence_score": round(s_evidence, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "resolution_state_score": round(s_resolution, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "outcome_score": round(s_outcome, 4),
            "compliance_score": round(s_compliance, 4),
            "compliance_adjustment": round(compliance_adjustment, 4),
            "compliance_penalty": round(compliance_penalty_value, 4),
            "currency_validation_score": round(s_currency, 4),
            "currency_adjustment": round(currency_adjustment, 4),
            "degenerate_penalty": round(degen_penalty, 4),
        }

    if task_type == "task_d":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_reasons = list_f1(
            canonical_reason_codes(submitted.get("reason_codes", [])),
            canonical_reason_codes(gold.get("reason_codes", [])),
        )
        s_policy = policy_score(submitted.get("policy_checks", {}), gold.get("policy_checks", {}))
        s_evidence = evidence_score(submitted.get("evidence_map", {}), gold.get("evidence_targets", {}), graph_state=graph_state)
        s_counter = counterfactual_score(submitted.get("counterfactual", ""), graph_state=graph_state)
        s_pressure = pressure_event_score(final_state)
        s_callback = callback_interpretation_score(submitted, final_state, gold)
        raw = (
            0.15 * s_decision
            + 0.15 * s_reasons
            + 0.12 * s_policy
            + 0.11 * s_evidence
            + 0.05 * s_counter
            + 0.08 * s_investigation
            + 0.07 * s_intervention
            + 0.05 * s_resolution
            + 0.04 * s_calibration
            + 0.03 * s_efficiency
            + 0.06 * s_outcome
            + 0.05 * s_pressure
            + 0.04 * s_callback
        ) + degen_penalty + compliance_adjustment + currency_adjustment
        if normalize_text(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.65
        return strict_task_score(raw), {
            "decision_score": round(s_decision, 4),
            "reason_score": round(s_reasons, 4),
            "policy_score": round(s_policy, 4),
            "evidence_score": round(s_evidence, 4),
            "counterfactual_score": round(s_counter, 4),
            "investigation_score": round(s_investigation, 4),
            "intervention_score": round(s_intervention, 4),
            "resolution_state_score": round(s_resolution, 4),
            "calibration_score": round(s_calibration, 4),
            "efficiency_score": round(s_efficiency, 4),
            "outcome_score": round(s_outcome, 4),
            "pressure_event_score": round(s_pressure, 4),
            "callback_interpretation_score": round(s_callback, 4),
            "compliance_score": round(s_compliance, 4),
            "compliance_adjustment": round(compliance_adjustment, 4),
            "compliance_penalty": round(compliance_penalty_value, 4),
            "currency_validation_score": round(s_currency, 4),
            "currency_adjustment": round(currency_adjustment, 4),
            "degenerate_penalty": round(degen_penalty, 4),
        }

    if task_type == "task_e":
        s_decision = decision_score(submitted.get("decision", ""), gold.get("decision", ""))
        s_links, link_stats = task_e_cross_invoice_link_score(
            submitted.get("cross_invoice_links", []) or submitted.get("duplicate_links", []),
            gold.get("cross_invoice_links", []) or gold.get("duplicate_links", []),
        )
        s_campaign = list_f1(
            submitted.get("campaign_signals", []),
            gold.get("campaign_signals", []),
        )
        s_policy = policy_score(submitted.get("policy_checks", {}), gold.get("policy_checks", {}))
        s_evidence = evidence_score(
            submitted.get("evidence_map", {}),
            gold.get("evidence_targets", {}),
            empty_cap=TASK_E_DEGENERATE_EVIDENCE_CAP,
            graph_state=graph_state,
        )
        s_counter, counter_stats = task_e_counterfactual_score(
            submitted.get("counterfactual", ""),
            gold,
            case_context,
        )
        s_pressure = pressure_event_score(final_state)
        raw = (
            0.18 * s_decision
            + 0.22 * s_links
            + 0.18 * s_campaign
            + 0.10 * s_policy
            + 0.10 * s_evidence
            + 0.08 * s_counter
            + 0.08 * s_intervention
            + 0.06 * s_pressure
        ) + degen_penalty + compliance_adjustment + currency_adjustment
        if normalize_text(submitted.get("decision", "")) == "pay" and gold.get("unsafe_if_pay", False):
            raw -= 0.80
        required_links = min(2, max(link_stats["gold_links"], 1))
        if raw > TASK_E_LINK_GATE_THRESHOLD and link_stats["matched_links"] < required_links:
            raw = min(raw, TASK_E_LINK_GATE_THRESHOLD - 0.01)
        if raw > TASK_E_LINK_GATE_THRESHOLD and counter_stats["doc_refs"] < required_links:
            raw = min(raw, TASK_E_LINK_GATE_THRESHOLD - 0.01)
        return strict_task_score(raw), {
            "decision_score": round(s_decision, 4),
            "cross_invoice_link_score": round(s_links, 4),
            "campaign_detection_score": round(s_campaign, 4),
            "policy_score": round(s_policy, 4),
            "evidence_score": round(s_evidence, 4),
            "counterfactual_score": round(s_counter, 4),
            "intervention_score": round(s_intervention, 4),
            "pressure_event_score": round(s_pressure, 4),
            "compliance_score": round(s_compliance, 4),
            "compliance_adjustment": round(compliance_adjustment, 4),
            "compliance_penalty": round(compliance_penalty_value, 4),
            "currency_validation_score": round(s_currency, 4),
            "currency_adjustment": round(currency_adjustment, 4),
            "cross_invoice_link_matches": round(float(link_stats["matched_links"]), 4),
            "counterfactual_doc_refs": round(float(counter_stats["doc_refs"]), 4),
            "degenerate_penalty": round(degen_penalty, 4),
        }

    return strict_task_score(0.0), {"error": 0.0}
