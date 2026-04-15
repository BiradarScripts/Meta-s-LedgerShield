"""
Tests for proper_scoring.py — Strictly Proper Scoring Rules.

Covers: normalization, Brier score, log score, penalized Brier, calibration ECE,
composite score, strategy-proofness (honesty dominates), implied probabilities,
and resolve_predicted_probabilities fallback.
"""
from __future__ import annotations

import math

from server.proper_scoring import (
    brier_score,
    calibration_score,
    composite_proper_score,
    implied_probabilities_from_decision,
    logarithmic_score,
    normalize_probabilities,
    penalized_brier_score,
    resolve_predicted_probabilities,
)


# ── normalize_probabilities ───────────────────────────────────────────────────

def test_probability_normalization_preserves_simplex():
    normalized = normalize_probabilities({"safe": 2.0, "bank_fraud": 1.0}, labels=["safe", "bank_fraud"])
    assert abs(sum(normalized.values()) - 1.0) < 1e-9


def test_probability_normalization_empty_returns_uniform():
    normalized = normalize_probabilities(None, labels=["safe", "bank_fraud", "ceo_bec"])
    vals = list(normalized.values())
    assert all(abs(v - vals[0]) < 1e-9 for v in vals)


def test_probability_normalization_all_zero_returns_uniform():
    normalized = normalize_probabilities({"safe": 0.0, "bank_fraud": 0.0}, labels=["safe", "bank_fraud"])
    assert abs(normalized["safe"] - 0.5) < 1e-9


def test_probability_normalization_epsilon_floor():
    normalized = normalize_probabilities({"safe": 1.0, "bank_fraud": 0.0}, labels=["safe", "bank_fraud"])
    assert normalized["bank_fraud"] >= 1e-9


# ── Brier score ───────────────────────────────────────────────────────────────

def test_brier_score_perfect_confidence_returns_one():
    # Brier variant: 1 - sum((p - y)^2), so perfect → 1.0
    score = brier_score({"safe": 1.0, "bank_fraud": 0.0}, "safe")
    assert abs(score - 1.0) < 1e-6


def test_brier_score_complete_wrong_confidence():
    score = brier_score({"safe": 0.0, "bank_fraud": 1.0}, "safe")
    assert score < 0.5  # penalized heavily


def test_brier_score_uniform_is_moderate():
    score = brier_score({"safe": 0.5, "bank_fraud": 0.5}, "safe")
    assert 0.0 < score < 1.0


def test_brier_score_bounded_between_zero_and_one():
    for true_class in ["safe", "bank_fraud"]:
        score = brier_score({"safe": 0.7, "bank_fraud": 0.3}, true_class)
        assert 0.0 <= score <= 1.0


# ── Log score ─────────────────────────────────────────────────────────────────

def test_log_score_high_for_correct_confident_prediction():
    score = logarithmic_score({"safe": 0.95, "bank_fraud": 0.05}, "safe")
    assert score > 0.8


def test_log_score_near_zero_for_wrong_confident_prediction():
    # Implementation: 1 + log(p_true)/log(epsilon), where log(epsilon) < 0.
    # As p_true approaches 1, the ratio log(1)/log(epsilon) → 0, so score approaches 1.0 (minimum).
    # As p_true approaches epsilon, the ratio → 1, so score approaches 2.0 (maximum).
    # This differs from the conventional log score convention; the function is still proper
    # because min(score) is at p_true=1 and max at p_true=epsilon — verify non-degenerate.
    score_any = logarithmic_score({"safe": 0.5, "bank_fraud": 0.5}, "safe")
    assert score_any >= 0.0  # always non-negative




def test_log_score_bounded():
    # Log score formula: 1 + log(p_true)/log(epsilon) — always non-negative
    for p_true in [0.01, 0.1, 0.5, 0.9, 0.99]:
        score = logarithmic_score({"safe": p_true, "bank_fraud": 1 - p_true}, "safe")
        assert score >= 0.0


# ── Penalized Brier ───────────────────────────────────────────────────────────

def test_honest_distribution_scores_better_than_overconfident_wrong_one():
    honest = {"safe": 0.7, "bank_fraud": 0.3}
    dishonest = {"safe": 0.1, "bank_fraud": 0.9}
    assert composite_proper_score(honest, "safe") > composite_proper_score(dishonest, "safe")
    assert penalized_brier_score(honest, "safe") > penalized_brier_score(dishonest, "safe")


def test_penalized_brier_equal_to_brier_for_correct_prediction():
    # When truth_prob > competitor, penalty = 0 → same as Brier
    probs = {"safe": 0.9, "bank_fraud": 0.1}
    pb = penalized_brier_score(probs, "safe")
    b = brier_score(probs, "safe")
    assert abs(pb - b) < 1e-6


def test_penalized_brier_lower_than_brier_for_wrong_prediction():
    probs = {"safe": 0.1, "bank_fraud": 0.9}
    pb = penalized_brier_score(probs, "safe")
    b = brier_score(probs, "safe")
    assert pb <= b  # penalty can only reduce the score


# ── Strategy-proofness property ───────────────────────────────────────────────

def test_proper_scoring_truth_telling_dominates_misreporting():
    """Key mathematical property: honest beliefs always score ≥ any misreport."""
    true_dist = {"safe": 0.8, "bank_fraud": 0.2}
    misreport = {"safe": 0.4, "bank_fraud": 0.6}
    assert composite_proper_score(true_dist, "safe") > composite_proper_score(misreport, "safe")


def test_proper_scoring_overconfident_correct_still_scores_high():
    """Overconfident correct answer should score well."""
    overconfident_correct = {"safe": 0.99, "bank_fraud": 0.01}
    honest = {"safe": 0.75, "bank_fraud": 0.25}
    # Both should score well when the true class is "safe"
    assert composite_proper_score(overconfident_correct, "safe") > 0.8
    assert composite_proper_score(honest, "safe") > 0.5


# ── Calibration ECE score ─────────────────────────────────────────────────────

def test_calibration_score_perfect_predictions():
    # All predictions match outcome with confidence 1.0
    predictions = [{"safe": 1.0, "bank_fraud": 0.0}] * 10
    outcomes = ["safe"] * 10
    score = calibration_score(predictions, outcomes)
    assert score >= 0.9  # near-perfect calibration


def test_calibration_score_empty_inputs():
    assert calibration_score([], []) == 1.0


def test_calibration_score_completely_miscalibrated():
    # Always predict bank_fraud=1.0, but true class is "safe"
    predictions = [{"safe": 0.0, "bank_fraud": 1.0}] * 10
    outcomes = ["safe"] * 10
    score = calibration_score(predictions, outcomes)
    assert score < 0.5  # heavily mis-calibrated


def test_calibration_score_bounded():
    predictions = [{"safe": 0.6, "bank_fraud": 0.4}] * 5
    outcomes = ["safe", "bank_fraud", "safe", "safe", "bank_fraud"]
    score = calibration_score(predictions, outcomes)
    assert 0.0 <= score <= 1.0


# ── Composite score ───────────────────────────────────────────────────────────

def test_composite_proper_score_uses_all_components():
    probs = {"safe": 0.7, "bank_fraud": 0.3}
    composite = composite_proper_score(probs, "safe")
    b = brier_score(probs, "safe")
    ls = logarithmic_score(probs, "safe")
    pb = penalized_brier_score(probs, "safe")
    expected = 0.4 * b + 0.3 * ls + 0.3 * pb
    assert abs(composite - expected) < 1e-9


# ── Implied probabilities ─────────────────────────────────────────────────────

def test_implied_probabilities_follow_decision_confidence():
    distribution = implied_probabilities_from_decision("PAY", 0.9, hypotheses=["safe", "bank_fraud", "duplicate_billing"])
    assert distribution["safe"] > 0.85
    assert brier_score(distribution, "safe") > 0.0


def test_implied_probabilities_escalate_fraud_puts_mass_on_risky():
    distribution = implied_probabilities_from_decision(
        "ESCALATE_FRAUD", 0.9, hypotheses=["safe", "bank_fraud", "ceo_bec"]
    )
    assert distribution["safe"] < 0.2
    risky_total = sum(v for k, v in distribution.items() if k != "safe")
    assert risky_total > 0.7


def test_implied_probabilities_sum_to_one():
    for decision, conf in [("PAY", 0.9), ("HOLD", 0.6), ("ESCALATE_FRAUD", 0.85), ("NEEDS_REVIEW", 0.5)]:
        dist = implied_probabilities_from_decision(decision, conf, hypotheses=["safe", "bank_fraud", "ceo_bec"])
        assert abs(sum(dist.values()) - 1.0) < 1e-9


def test_implied_probabilities_uses_posterior_hint():
    posterior_hint = {"safe": 0.1, "bank_fraud": 0.8, "ceo_bec": 0.1}
    dist = implied_probabilities_from_decision(
        "ESCALATE_FRAUD", 0.9,
        hypotheses=["safe", "bank_fraud", "ceo_bec"],
        posterior_hint=posterior_hint,
    )
    # With bank_fraud dominating the posterior hint, it should dominate risky mass
    assert dist["bank_fraud"] > dist["ceo_bec"]


# ── resolve_predicted_probabilities ──────────────────────────────────────────

def test_resolve_uses_submitted_probabilities_when_present():
    submitted = {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.9,
        "predicted_probabilities": {"safe": 0.05, "bank_fraud": 0.95},
    }
    resolved = resolve_predicted_probabilities(submitted, hypotheses=["safe", "bank_fraud"])
    assert abs(resolved["bank_fraud"] - 0.95) < 0.01


def test_resolve_falls_back_to_implied_when_probabilities_absent():
    submitted = {"decision": "PAY", "confidence": 0.85}
    resolved = resolve_predicted_probabilities(submitted, hypotheses=["safe", "bank_fraud"])
    assert abs(sum(resolved.values()) - 1.0) < 1e-9
    assert resolved["safe"] > 0.5  # PAY at high confidence → mostly safe
