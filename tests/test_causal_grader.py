"""
Tests for causal_grader.py — Pearl's three-layer causal grading.

Covers: association scoring, interventional scoring, d-separation sufficiency,
counterfactual alignment, grade_causal_consistency, causal_grade_adjustment.
"""
from __future__ import annotations

from server.causal_grader import (
    CausalGrade,
    _counterfactual_alignment,
    _list_f1,
    causal_grade_adjustment,
    grade_causal_consistency,
)
from server.causal_model import build_causal_model_for_case
from server.data_loader import load_all


# ── List F1 helper ───────────────────────────────────────────────────────────

def test_list_f1_perfect_match():
    assert _list_f1(["bank_fraud", "duplicate"], ["bank_fraud", "duplicate"]) == 1.0


def test_list_f1_zero_overlap():
    assert _list_f1(["bank_fraud"], ["ceo_bec"]) == 0.0


def test_list_f1_partial():
    score = _list_f1(["bank_fraud", "ceo_bec"], ["bank_fraud"])
    assert 0.0 < score < 1.0


def test_list_f1_empty_both():
    assert _list_f1([], []) == 1.0


def test_list_f1_empty_pred():
    assert _list_f1([], ["bank_fraud"]) == 0.0


# ── Counterfactual alignment ─────────────────────────────────────────────────

def test_counterfactual_alignment_empty_text_returns_zero():
    db = load_all()
    scm = build_causal_model_for_case(db["cases_by_id"]["CASE-D-001"])
    score = _counterfactual_alignment("", scm)
    assert score == 0.0


def test_counterfactual_alignment_with_relevant_keywords():
    db = load_all()
    scm = build_causal_model_for_case(db["cases_by_id"]["CASE-D-001"])
    text = "Would ESCALATE_FRAUD if the bank account did not match and callback was disputed."
    score = _counterfactual_alignment(text, scm)
    assert score > 0.0


def test_counterfactual_alignment_capped_at_one():
    db = load_all()
    scm = build_causal_model_for_case(db["cases_by_id"]["CASE-D-001"])
    long_text = "escalate_fraud bank callback duplicate approval sender " * 20
    score = _counterfactual_alignment(long_text, scm)
    assert score <= 1.0


# ── grade_causal_consistency ─────────────────────────────────────────────────

def _minimal_context(case_id: str) -> dict:
    db = load_all()
    return db["cases_by_id"][case_id]


def test_causal_grader_correct_decision_boosts_association():
    case = _minimal_context("CASE-D-001")
    gold = case["gold"]
    submitted = {
        "decision": gold["decision"],
        "reason_codes": gold.get("reason_codes", []),
        "counterfactual": "",
    }
    grade = grade_causal_consistency(
        submitted=submitted,
        gold=gold,
        trajectory=[],
        case_context=case,
    )
    assert isinstance(grade, CausalGrade)
    assert grade.association_score > 0.5


def test_causal_grader_wrong_decision_lowers_association():
    case = _minimal_context("CASE-D-001")
    gold = case["gold"]
    wrong_decision = "PAY" if gold["decision"] != "PAY" else "ESCALATE_FRAUD"
    submitted = {
        "decision": wrong_decision,
        "reason_codes": [],
        "counterfactual": "",
    }
    grade = grade_causal_consistency(
        submitted=submitted,
        gold=gold,
        trajectory=[],
        case_context=case,
    )
    assert grade.association_score < 0.6


def test_causal_grader_rewards_interventional_coverage():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001"]
    gold = case["gold"]
    trajectory = [
        {"step": 1, "action_type": "inspect_email_thread", "success": True},
        {"step": 2, "action_type": "compare_bank_account", "success": True},
        {"step": 3, "action_type": "request_callback_verification", "success": True},
    ]
    submitted = {
        "decision": gold["decision"],
        "reason_codes": gold.get("reason_codes", []),
        "counterfactual": "",
    }
    grade_covered = grade_causal_consistency(
        submitted=submitted,
        gold=gold,
        trajectory=trajectory,
        case_context=case,
    )
    grade_empty = grade_causal_consistency(
        submitted=submitted,
        gold=gold,
        trajectory=[],
        case_context=case,
    )
    assert grade_covered.intervention_score >= grade_empty.intervention_score


def test_causal_grader_d_separation_improves_with_observations():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001"]
    gold = case["gold"]
    trajectory_full = [
        {"step": 1, "action_type": "inspect_email_thread", "success": True},
        {"step": 2, "action_type": "compare_bank_account", "success": True},
        {"step": 3, "action_type": "lookup_vendor_history", "success": True},
        {"step": 4, "action_type": "request_callback_verification", "success": True},
    ]
    submitted = {"decision": gold["decision"], "reason_codes": [], "counterfactual": ""}
    grade = grade_causal_consistency(
        submitted=submitted, gold=gold, trajectory=trajectory_full, case_context=case
    )
    assert grade.d_separation_sufficiency_score >= 0.0
    assert grade.d_separation_sufficiency_score <= 1.0


def test_causal_grader_counterfactual_text_improves_score():
    case = _minimal_context("CASE-D-001")
    gold = case["gold"]
    submitted_with_cf = {
        "decision": gold["decision"],
        "reason_codes": gold.get("reason_codes", []),
        "counterfactual": "Would escalate_fraud if the bank or callback showed dispute.",
    }
    submitted_no_cf = {
        "decision": gold["decision"],
        "reason_codes": gold.get("reason_codes", []),
        "counterfactual": "",
    }
    grade_cf = grade_causal_consistency(
        submitted=submitted_with_cf, gold=gold, trajectory=[], case_context=case
    )
    grade_no = grade_causal_consistency(
        submitted=submitted_no_cf, gold=gold, trajectory=[], case_context=case
    )
    assert grade_cf.counterfactual_score >= grade_no.counterfactual_score


def test_causal_grade_overall_bounded():
    case = _minimal_context("CASE-D-001")
    gold = case["gold"]
    submitted = {"decision": gold["decision"], "reason_codes": [], "counterfactual": ""}
    grade = grade_causal_consistency(
        submitted=submitted, gold=gold, trajectory=[], case_context=case
    )
    assert 0.0 <= grade.overall_score <= 1.0


# ── causal_grade_adjustment ──────────────────────────────────────────────────

def test_causal_grade_adjustment_positive_for_good_grade():
    good_grade = CausalGrade(
        association_score=0.9,
        intervention_score=0.9,
        counterfactual_score=0.8,
        d_separation_sufficiency_score=1.0,
        overall_score=0.9,
        observed_nodes=[],
        required_actions=[],
    )
    adj = causal_grade_adjustment(good_grade, weight=0.05)
    assert adj > 0.0


def test_causal_grade_adjustment_negative_for_poor_grade():
    poor_grade = CausalGrade(
        association_score=0.1,
        intervention_score=0.0,
        counterfactual_score=0.0,
        d_separation_sufficiency_score=0.0,
        overall_score=0.05,
        observed_nodes=[],
        required_actions=[],
    )
    adj = causal_grade_adjustment(poor_grade, weight=0.05)
    assert adj < 0.0


def test_causal_grade_adjustment_neutral_at_half():
    mid_grade = CausalGrade(
        association_score=0.5,
        intervention_score=0.5,
        counterfactual_score=0.5,
        d_separation_sufficiency_score=0.5,
        overall_score=0.5,
        observed_nodes=[],
        required_actions=[],
    )
    adj = causal_grade_adjustment(mid_grade, weight=0.05)
    assert adj == 0.0
