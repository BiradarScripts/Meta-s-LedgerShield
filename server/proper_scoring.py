from __future__ import annotations

import math
from typing import Any

from .sprt_engine import DEFAULT_HYPOTHESES
from .schema import normalize_text


def normalize_probabilities(
    predicted_probabilities: dict[str, float] | None,
    *,
    labels: list[str] | None = None,
    epsilon: float = 1e-9,
) -> dict[str, float]:
    labels = list(labels or DEFAULT_HYPOTHESES)
    if not labels:
        return {}

    if not predicted_probabilities:
        base = 1.0 / len(labels)
        return {label: base for label in labels}

    cleaned = {
        label: max(0.0, float(predicted_probabilities.get(label, 0.0) or 0.0))
        for label in labels
    }
    total = sum(cleaned.values())
    if total <= 0.0:
        base = 1.0 / len(labels)
        return {label: base for label in labels}
    return {
        label: max(epsilon, value / total)
        for label, value in cleaned.items()
    }


def brier_score(predicted_probabilities: dict[str, float], true_class: str) -> float:
    probabilities = normalize_probabilities(predicted_probabilities, labels=list(predicted_probabilities.keys()) or None)
    truth = normalize_text(true_class)
    total = 0.0
    for label, probability in probabilities.items():
        indicator = 1.0 if normalize_text(label) == truth else 0.0
        total += (probability - indicator) ** 2
    return max(0.0, 1.0 - total)


def logarithmic_score(predicted_probabilities: dict[str, float], true_class: str) -> float:
    probabilities = normalize_probabilities(predicted_probabilities, labels=list(predicted_probabilities.keys()) or None)
    truth = normalize_text(true_class)
    truth_probability = next(
        (probability for label, probability in probabilities.items() if normalize_text(label) == truth),
        min(probabilities.values(), default=1e-9),
    )
    return max(0.0, 1.0 + (math.log(max(truth_probability, 1e-9)) / math.log(1e-9)))


def penalized_brier_score(
    predicted_probabilities: dict[str, float],
    true_class: str,
    penalty_weight: float = 0.3,
) -> float:
    probabilities = normalize_probabilities(predicted_probabilities, labels=list(predicted_probabilities.keys()) or None)
    truth = normalize_text(true_class)
    truth_probability = next(
        (probability for label, probability in probabilities.items() if normalize_text(label) == truth),
        0.0,
    )
    competitor = max(
        (probability for label, probability in probabilities.items() if normalize_text(label) != truth),
        default=0.0,
    )
    penalty = penalty_weight * max(0.0, competitor - truth_probability)
    return max(0.0, brier_score(probabilities, true_class) - penalty)


def calibration_score(
    predictions: list[dict[str, float]],
    outcomes: list[str],
    *,
    bins: int = 10,
) -> float:
    if not predictions or not outcomes:
        return 1.0

    bucket_totals = [0 for _ in range(bins)]
    bucket_confidence = [0.0 for _ in range(bins)]
    bucket_accuracy = [0.0 for _ in range(bins)]

    for prediction, outcome in zip(predictions, outcomes):
        normalized = normalize_probabilities(prediction, labels=list(prediction.keys()) or None)
        label, confidence = max(normalized.items(), key=lambda item: item[1])
        index = min(bins - 1, int(confidence * bins))
        bucket_totals[index] += 1
        bucket_confidence[index] += confidence
        bucket_accuracy[index] += float(normalize_text(label) == normalize_text(outcome))

    ece = 0.0
    total = sum(bucket_totals)
    for index in range(bins):
        count = bucket_totals[index]
        if count == 0:
            continue
        avg_confidence = bucket_confidence[index] / count
        avg_accuracy = bucket_accuracy[index] / count
        ece += (count / total) * abs(avg_accuracy - avg_confidence)

    return max(0.0, 1.0 - ece)


def composite_proper_score(
    predicted_probabilities: dict[str, float],
    true_class: str,
    weights: dict[str, float] | None = None,
) -> float:
    weights = weights or {"brier": 0.4, "log": 0.3, "penalized": 0.3}
    probabilities = normalize_probabilities(predicted_probabilities, labels=list(predicted_probabilities.keys()) or None)
    return (
        weights.get("brier", 0.0) * brier_score(probabilities, true_class)
        + weights.get("log", 0.0) * logarithmic_score(probabilities, true_class)
        + weights.get("penalized", 0.0) * penalized_brier_score(probabilities, true_class)
    )


def implied_probabilities_from_decision(
    decision: str,
    confidence: float,
    *,
    hypotheses: list[str] | None = None,
    posterior_hint: dict[str, float] | None = None,
) -> dict[str, float]:
    hypotheses = list(hypotheses or DEFAULT_HYPOTHESES)
    confidence = max(0.0, min(1.0, float(confidence)))
    decision_norm = normalize_text(decision)
    posterior_hint = normalize_probabilities(posterior_hint, labels=hypotheses) if posterior_hint else None

    if posterior_hint is None:
        base = 1.0 / len(hypotheses)
        posterior_hint = {hypothesis: base for hypothesis in hypotheses}

    if decision_norm == "pay":
        distribution = {hypothesis: 0.0 for hypothesis in hypotheses}
        distribution["safe"] = confidence
        remainder = 1.0 - confidence
        risky_total = sum(probability for hypothesis, probability in posterior_hint.items() if hypothesis != "safe")
        for hypothesis in hypotheses:
            if hypothesis == "safe":
                continue
            weight = posterior_hint[hypothesis] / max(risky_total, 1e-9)
            distribution[hypothesis] = remainder * weight
        return normalize_probabilities(distribution, labels=hypotheses)

    risky_hypotheses = [hypothesis for hypothesis in hypotheses if hypothesis != "safe"]
    risky_total = sum(posterior_hint[hypothesis] for hypothesis in risky_hypotheses)
    distribution = {"safe": 1.0 - confidence}
    for hypothesis in risky_hypotheses:
        weight = posterior_hint[hypothesis] / max(risky_total, 1e-9)
        distribution[hypothesis] = confidence * weight
    return normalize_probabilities(distribution, labels=hypotheses)


def resolve_predicted_probabilities(
    submitted: dict[str, Any],
    *,
    hypotheses: list[str] | None = None,
    posterior_hint: dict[str, float] | None = None,
) -> dict[str, float]:
    hypotheses = list(hypotheses or DEFAULT_HYPOTHESES)
    payload = submitted.get("predicted_probabilities")
    if isinstance(payload, dict) and payload:
        return normalize_probabilities(payload, labels=hypotheses)
    return implied_probabilities_from_decision(
        str(submitted.get("decision", "")),
        float(submitted.get("confidence", 0.5) or 0.5),
        hypotheses=hypotheses,
        posterior_hint=posterior_hint,
    )
