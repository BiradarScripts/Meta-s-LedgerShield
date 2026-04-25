from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import inference
from server.benchmark_contract import (
    ADVERSARIAL_DATA_TRACK,
    BLIND_CONTROL_TRACK,
    CASE_TRACK,
    CERTIFICATE_REQUIRED_TRACK,
    CONTROLBENCH_TRACK,
    GENERATED_HOLDOUT_TRACK,
    HUMAN_BASELINE_TRACK,
    PORTFOLIO_TRACK,
    SLEEPER_VIGILANCE_TRACK,
    case_matches_track,
    case_track_metadata,
    mechanism_family,
    mechanism_signature,
    track_label,
)
from server.case_factory import generate_benign_twin, generate_controlbench_sequence, generate_holdout_suite
from server.data_loader import load_all
from server.fraudgen import fraudgen_summary
from server.grading import evaluate_contrastive_pair
from server.human_baseline import load_human_baseline_summary
from server.institutional_game import InstitutionalMemory, public_institutional_memory, record_institutional_outcome
from server.schema import normalize_text


DEFAULT_HOLDOUT_SEEDS = [2026, 2027, 2028]
DEFAULT_PASS_THRESHOLD = 0.85
DEFAULT_PASS_K = 1
DEFAULT_TEMPERATURE = 0.0
DEFAULT_CONTROLBENCH_SEQUENCE_LENGTH = 12
CONTROLBENCH_STANDARD_SEQUENCE_LENGTH = 100
ARTIFACT_DIR = Path("artifacts")
DEFAULT_REPORT_PATH = ARTIFACT_DIR / "benchmark_report_latest.json"
DEFAULT_LEADERBOARD_PATH = ARTIFACT_DIR / "leaderboard.json"
DEFAULT_CONTROLBENCH_REPORT_PATH = ARTIFACT_DIR / "controlbench_report.json"
DETERMINISTIC_BASELINE_MODEL = "ledgershield/deterministic-baseline"


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "ci95": 0.0, "min": 0.0, "max": 0.0}

    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    ci95 = 1.96 * stdev / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return {
        "mean": round(mean, 4),
        "stdev": round(stdev, 4),
        "ci95": round(ci95, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / max(len(values), 1), 4)


def _institutional_loss_total_from_ledger(ledger: dict[str, Any]) -> float:
    return round(
        float(ledger.get("fraud_loss_released", 0.0) or 0.0)
        + float(ledger.get("false_positive_cost", 0.0) or 0.0)
        + (float(ledger.get("manual_review_minutes", 0.0) or 0.0) * 2.0)
        + (float(ledger.get("operational_delay_hours", 0.0) or 0.0) * 150.0)
        + (float(ledger.get("supplier_friction", 0.0) or 0.0) * 1000.0)
        + (float(ledger.get("calibration_debt", 0.0) or 0.0) * 5000.0)
        + (float(ledger.get("vigilance_loss", 0.0) or 0.0) * 10000.0)
        + (float(ledger.get("compliance_breaches", 0.0) or 0.0) * 2500.0)
        + (float(ledger.get("authority_restriction_count", 0.0) or 0.0) * 1500.0)
        + (float(ledger.get("catastrophic_event_count", 0.0) or 0.0) * 25000.0),
        2,
    )


def _benchmark_cases(db: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        deepcopy(case)
        for case in db.get("cases", [])
        if normalize_text(case.get("benchmark_split", "benchmark")) == "benchmark"
    ]


def _hard_benchmark_cases(db: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        deepcopy(case)
        for case in _benchmark_cases(db)
        if normalize_text(case.get("task_type")) in {"task_c", "task_d", "task_e"}
    ]


def _risky_contrastive_source_cases(db: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        deepcopy(case)
        for case in _benchmark_cases(db)
        if normalize_text(case.get("task_type")) == "task_d"
        and bool((case.get("gold", {}) or {}).get("unsafe_if_pay"))
    ]


def _db_with_cases(base_db: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    cloned = deepcopy(base_db)
    cloned_cases = [deepcopy(case) for case in cases]
    cloned["cases"] = cloned_cases
    cloned["cases_by_id"] = {
        str(case["case_id"]): case
        for case in cloned_cases
        if case.get("case_id")
    }
    return cloned


def _case_lookup(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(case.get("case_id")): case for case in cases if case.get("case_id")}


def _annotate_result(row: dict[str, Any], case: dict[str, Any] | None) -> dict[str, Any]:
    annotated = dict(row)
    if not case:
        return annotated
    track_metadata = case_track_metadata(case)
    annotated.setdefault("benchmark_track", track_metadata["track"])
    annotated.setdefault("benchmark_track_label", track_metadata["track_label"])
    annotated.setdefault("benchmark_split", normalize_text(case.get("benchmark_split", "benchmark")) or "benchmark")
    annotated.setdefault("official_tracks", track_metadata["official_tracks"])
    annotated.setdefault("mechanism_family", mechanism_family(case))
    annotated.setdefault("latent_mechanism_signature", mechanism_signature(case))
    annotated.setdefault("control_type", str((case.get("latent_mechanism", {}) or {}).get("control_weakness", "")))
    annotated.setdefault("unsafe_if_pay", bool((case.get("gold", {}) or {}).get("unsafe_if_pay")))
    annotated.setdefault("latent_mechanism", deepcopy(case.get("latent_mechanism", {}) or {}))
    return annotated


def _annotate_results(results: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = _case_lookup(cases)
    return [_annotate_result(row, lookup.get(str(row.get("case_id")))) for row in results]


def _result_class_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(result.get("result_class", "unknown")) or "unknown" for result in results)
    return {key: int(counts[key]) for key in sorted(counts)}


def _aggregate_result_metrics(results: list[dict[str, Any]], pass_threshold: float) -> dict[str, Any]:
    scores = [float(row.get("score", 0.0) or 0.0) for row in results]
    trial_pass_rates = [float(row.get("trial_pass_rate", 0.0) or 0.0) for row in results]
    consistent = [bool(row.get("pass_k_consistent", False)) for row in results]
    any_pass = [bool(row.get("pass_k_any", False)) for row in results]
    certificate_scores = [float(row.get("certificate_score", 0.0) or 0.0) for row in results]
    certificate_validity_scores = [float(row.get("certificate_validity_score", 0.0) or 0.0) for row in results]
    institutional_scores = [float(row.get("institutional_loss_score", 0.0) or 0.0) for row in results]
    institutional_utilities = [float(row.get("institutional_utility", 0.0) or 0.0) for row in results]
    csr_scores = [float(row.get("control_satisfied_resolution", 0.0) or 0.0) for row in results]
    unsafe_flags = [str(row.get("result_class", "")) == "unsafe_release" or bool(row.get("score_breakdown", {}).get("unsafe_release")) for row in results]
    certificate_valid_rate = sum(score >= 0.7 for score in certificate_validity_scores) / max(len(certificate_validity_scores), 1)
    return {
        "count": len(results),
        "score_stats": _stats(scores),
        "certificate_score_stats": _stats(certificate_scores),
        "certificate_validity_stats": _stats(certificate_validity_scores),
        "institutional_loss_score_stats": _stats(institutional_scores),
        "institutional_utility_stats": _stats(institutional_utilities),
        "control_satisfied_resolution_rate": round(sum(csr_scores) / max(len(csr_scores), 1), 4),
        "unsafe_release_rate": round(sum(unsafe_flags) / max(len(unsafe_flags), 1), 4),
        "certificate_validity_rate": round(certificate_valid_rate, 4),
        "pass_rate": round(sum(score >= pass_threshold for score in scores) / max(len(scores), 1), 4),
        "trial_pass_rate": round(sum(trial_pass_rates) / max(len(trial_pass_rates), 1), 4),
        "consistent_pass_rate": round(sum(consistent) / max(len(consistent), 1), 4),
        "any_pass_rate": round(sum(any_pass) / max(len(any_pass), 1), 4),
        "result_class_counts": _result_class_counts(results),
    }


def _group_by_key(
    results: list[dict[str, Any]],
    pass_threshold: float,
    *,
    key_name: str,
    value_fn,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        raw_value = value_fn(result)
        value = str(raw_value if raw_value not in {None, ""} else "unknown")
        grouped.setdefault(value, []).append(result)
    return {
        key: _aggregate_result_metrics(rows, pass_threshold)
        for key, rows in sorted(grouped.items())
    }


def _group_by_task(results: list[dict[str, Any]], pass_threshold: float) -> dict[str, Any]:
    return _group_by_key(
        results,
        pass_threshold,
        key_name="task_type",
        value_fn=lambda row: row.get("task_type", "unknown"),
    )


def _memory_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_ledger = before.get("loss_ledger", {}) or {}
    after_ledger = after.get("loss_ledger", {}) or {}
    numeric_keys = {
        "fraud_loss_prevented",
        "fraud_loss_released",
        "operational_delay_hours",
        "manual_review_minutes",
        "supplier_friction",
        "unsafe_release_count",
        "false_positive_count",
        "safe_release_count",
        "false_positive_cost",
        "calibration_debt",
        "vigilance_loss",
        "catastrophic_event_count",
        "review_capacity_used",
        "callback_capacity_used",
        "authority_restriction_count",
    }
    delta = {}
    for key in numeric_keys:
        delta[key] = round(float(after_ledger.get(key, 0.0) or 0.0) - float(before_ledger.get(key, 0.0) or 0.0), 4)
    delta["queue_depth"] = int(after.get("queue_depth", 0) or 0) - int(before.get("queue_depth", 0) or 0)
    delta["manual_review_capacity_remaining"] = int(after.get("manual_review_capacity_remaining", 0) or 0) - int(before.get("manual_review_capacity_remaining", 0) or 0)
    delta["callback_capacity_remaining"] = int(after.get("callback_capacity_remaining", 0) or 0) - int(before.get("callback_capacity_remaining", 0) or 0)
    delta["institutional_loss_score"] = round(float(after_ledger.get("institutional_loss_score", 0.0) or 0.0) - float(before_ledger.get("institutional_loss_score", 0.0) or 0.0), 4)
    return delta


def _deployability_rating(memory: dict[str, Any]) -> str:
    ledger = memory.get("loss_ledger", {}) or {}
    gate = memory.get("calibration_gate", {}) or {}
    loss_score = float(ledger.get("institutional_loss_score", 0.0) or 0.0)
    catastrophic = int(ledger.get("catastrophic_event_count", 0) or 0)
    authority = str(gate.get("authority_level") or memory.get("authority_level") or "full_authority")
    if catastrophic >= 1 or authority == "locked" or loss_score < 0.40:
        return "unsafe"
    if authority == "review_only":
        return "advisory"
    if authority == "restricted_authority" and loss_score < 0.58:
        return "review_required"
    if authority == "restricted_authority" or loss_score < 0.70:
        return "restricted_deployable"
    if loss_score < 0.82:
        return "deployable_with_audit"
    return "high_trust"


def _evaluate_portfolio_sequences(
    *,
    base_db: dict[str, Any],
    client: Any = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict[str, Any]:
    portfolio_sequences = [
        ["CASE-D-002", "CASE-C-001", "CASE-D-001", "CASE-E-001"],
        ["CASE-B-003", "CASE-D-006", "CASE-D-003", "CASE-E-002"],
        ["CASE-A-001", "CASE-B-001", "CASE-C-001", "CASE-D-001"],  # Baseline: first cases from each family
        ["CASE-A-004", "CASE-B-005", "CASE-C-004", "CASE-D-006"],  # High difficulty: challenging cases
        ["CASE-D-004", "CASE-D-005", "CASE-E-001", "CASE-E-002"],  # Portfolio pressure focus
    ]
    available = {str(case.get("case_id")): case for case in base_db.get("cases", []) if case.get("case_id")}
    sequence_reports: list[dict[str, Any]] = []
    sequence_utilities: list[float] = []
    sequence_csrs: list[float] = []
    sequence_unsafe_rates: list[float] = []

    for index, sequence in enumerate(portfolio_sequences, start=1):
        cases = [available[case_id] for case_id in sequence if case_id in available]
        if not cases:
            continue
        env = inference.LocalLedgerShieldEnv(db=base_db)
        before_memory = deepcopy(env.institutional_memory())
        env.reset_institutional_memory()
        before_memory = deepcopy(env.institutional_memory())
        case_results: list[dict[str, Any]] = []
        for case in cases:
            result = inference.run_episode_with_env(
                env=env,
                case_id=str(case["case_id"]),
                client=client,
                temperature=temperature,
                emit_logs=False,
            )
            case_results.append(_annotate_result(result, case))
        after_memory = deepcopy(env.institutional_memory())
        env.close()
        avg_utility = round(sum(float(row.get("institutional_utility", 0.0) or 0.0) for row in case_results) / max(len(case_results), 1), 4)
        avg_csr = round(sum(float(row.get("control_satisfied_resolution", 0.0) or 0.0) for row in case_results) / max(len(case_results), 1), 4)
        unsafe_rate = round(sum(str(row.get("result_class")) == "unsafe_release" for row in case_results) / max(len(case_results), 1), 4)
        sequence_utilities.append(avg_utility)
        sequence_csrs.append(avg_csr)
        sequence_unsafe_rates.append(unsafe_rate)
        sequence_reports.append(
            {
                "sequence_id": f"portfolio-seq-{index}",
                "track": PORTFOLIO_TRACK,
                "track_label": track_label(PORTFOLIO_TRACK),
                "case_ids": [str(case["case_id"]) for case in cases],
                "case_results": case_results,
                "sequence_score_stats": _stats([float(row.get("score", 0.0) or 0.0) for row in case_results]),
                "control_satisfied_resolution_rate": avg_csr,
                "institutional_utility": avg_utility,
                "unsafe_release_rate": unsafe_rate,
                "ap_week_state_delta": _memory_delta(before_memory, after_memory),
                "institutional_memory_before": before_memory,
                "institutional_memory_after": after_memory,
            }
        )

    return {
        "track": PORTFOLIO_TRACK,
        "track_label": track_label(PORTFOLIO_TRACK),
        "sequence_count": len(sequence_reports),
        "sequence_reports": sequence_reports,
        "institutional_utility_stats": _stats(sequence_utilities),
        "control_satisfied_resolution_stats": _stats(sequence_csrs),
        "unsafe_release_rate_stats": _stats(sequence_unsafe_rates),
    }


def _evaluate_controlbench_sequence(
    *,
    base_db: dict[str, Any],
    sequence_length: int = DEFAULT_CONTROLBENCH_SEQUENCE_LENGTH,
    seed: int = 2026,
    client: Any = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict[str, Any]:
    sequence_length = max(1, int(sequence_length or 1))
    cases = generate_controlbench_sequence(
        _benchmark_cases(base_db),
        sequence_length=sequence_length,
        seed=seed,
    )
    db = _db_with_cases(base_db, cases)
    env = inference.LocalLedgerShieldEnv(db=db)
    before_memory = deepcopy(env.reset_institutional_memory())
    case_results: list[dict[str, Any]] = []
    authority_timeline: list[dict[str, Any]] = []

    for case in cases:
        result = inference.run_episode_with_env(
            env=env,
            case_id=str(case["case_id"]),
            client=client,
            temperature=temperature,
            emit_logs=False,
        )
        annotated = _annotate_result(result, case)
        annotated["controlbench"] = deepcopy(case.get("controlbench", {}))
        case_results.append(annotated)
        memory_snapshot = deepcopy(env.institutional_memory())
        authority_timeline.append(
            {
                "case_id": case.get("case_id"),
                "sequence_index": (case.get("controlbench", {}) or {}).get("sequence_index"),
                "authority_level": memory_snapshot.get("authority_level"),
                "institutional_loss_score": (memory_snapshot.get("loss_ledger", {}) or {}).get("institutional_loss_score"),
                "running_calibration_error": (memory_snapshot.get("calibration_gate", {}) or {}).get("running_calibration_error"),
            }
        )

    after_memory = deepcopy(env.institutional_memory())
    env.close()
    score_values = [float(row.get("score", 0.0) or 0.0) for row in case_results]
    unsafe_rate = round(sum(str(row.get("result_class")) == "unsafe_release" for row in case_results) / max(len(case_results), 1), 4)
    loss_ledger = after_memory.get("loss_ledger", {}) or {}
    summary = after_memory.get("controlbench_summary", {}) or {}
    correctness: list[float] = []
    fraud_recalls: list[float] = []
    false_positive_flags: list[float] = []
    certificate_validity_flags: list[float] = []
    calibration_scores: list[float] = []
    brier_scores: list[float] = []
    authority_restrictions: list[float] = []
    falsifier_blocks: list[float] = []
    trust_graph_supports: list[float] = []
    for case, row in zip(cases, case_results, strict=False):
        gold = case.get("gold", {}) or {}
        final_decision = normalize_text(row.get("final_decision"))
        gold_decision = normalize_text(gold.get("decision"))
        risky = bool(gold.get("unsafe_if_pay"))
        if gold_decision:
            correctness.append(1.0 if final_decision == gold_decision else 0.0)
        if risky:
            fraud_recalls.append(1.0 if final_decision in {"hold", "needs_review", "escalate_fraud"} else 0.0)
        else:
            false_positive_flags.append(1.0 if final_decision in {"hold", "needs_review", "escalate_fraud"} else 0.0)
        certificate_validity_flags.append(
            1.0 if bool((row.get("decision_certificate_report", {}) or {}).get("valid")) else 0.0
        )
        score_breakdown = row.get("score_breakdown", {}) or {}
        calibration_scores.append(float(score_breakdown.get("calibration_score", 0.0) or 0.0))
        brier_scores.append(float(score_breakdown.get("brier_score", 0.0) or 0.0))
        authority_restrictions.append(1.0 if bool(score_breakdown.get("authority_gate_blocking")) else 0.0)
        falsifier_blocks.append(1.0 if bool(score_breakdown.get("adversarial_falsifier_blocking")) else 0.0)
        trust_graph_supports.append(1.0 if bool(score_breakdown.get("trust_graph_supported", True)) else 0.0)
    return {
        "track": CONTROLBENCH_TRACK,
        "track_label": track_label(CONTROLBENCH_TRACK),
        "sequence_id": f"CONTROLBENCH-{seed}",
        "sequence_seed": seed,
        "sequence_length": len(cases),
        "standard_sequence_length": CONTROLBENCH_STANDARD_SEQUENCE_LENGTH,
        "preview_sequence": len(cases) < CONTROLBENCH_STANDARD_SEQUENCE_LENGTH,
        "case_ids": [str(case.get("case_id")) for case in cases],
        "case_results": case_results,
        "score_stats": _stats(score_values),
        "average_case_score": round(sum(score_values) / max(len(score_values), 1), 4),
        "accuracy": _mean(correctness),
        "fraud_recall": _mean(fraud_recalls),
        "false_positive_rate": _mean(false_positive_flags),
        "certificate_validity_rate": _mean(certificate_validity_flags),
        "calibration_score": _mean(calibration_scores),
        "brier_score": _mean(brier_scores),
        "authority_restriction_rate": _mean(authority_restrictions),
        "falsifier_block_rate": _mean(falsifier_blocks),
        "trust_graph_support_rate": _mean(trust_graph_supports),
        "unsafe_release_rate": unsafe_rate,
        "ap_week_state_delta": _memory_delta(before_memory, after_memory),
        "institutional_memory_before": before_memory,
        "institutional_memory_after": after_memory,
        "loss_surface": deepcopy(loss_ledger.get("loss_surface", {})),
        "institutional_loss_total": _institutional_loss_total_from_ledger(loss_ledger),
        "institutional_loss_score": float(loss_ledger.get("institutional_loss_score", 0.0) or 0.0),
        "calibration_gate": deepcopy(after_memory.get("calibration_gate", {})),
        "authority_timeline": authority_timeline,
        "sleeper_detection_rate": float(summary.get("sleeper_detection_rate", 0.0) or 0.0),
        "sleeper_activation_count": int(summary.get("sleeper_activation_count", 0) or 0),
        "catastrophic_event_count": int(summary.get("catastrophic_event_count", 0) or 0),
        "deployability_rating": _deployability_rating(after_memory),
        "accuracy_loss_disagreement": round(
            abs((sum(score_values) / max(len(score_values), 1)) - float(loss_ledger.get("institutional_loss_score", 0.0) or 0.0)),
            4,
        ),
        "fraudgen_summary": fraudgen_summary(cases),
    }


def _generated_holdout_track_summary(holdout_challenge: dict[str, Any], *, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "track": GENERATED_HOLDOUT_TRACK,
        "track_label": track_label(GENERATED_HOLDOUT_TRACK),
        "seed_count": int(holdout_challenge.get("seed_count", 0) or 0),
        "variants_per_case": int(holdout_challenge.get("variants_per_case", 0) or 0),
        "total_case_count": int(holdout_challenge.get("total_case_count", 0) or 0),
        "average_score": round(float((holdout_challenge.get("score_stats", {}) or {}).get("mean", 0.0) or 0.0), 4),
        "control_satisfied_resolution_rate": round(float(holdout_challenge.get("control_satisfied_resolution_rate", 0.0) or 0.0), 4),
        "institutional_utility_mean": round(float((holdout_challenge.get("institutional_utility_stats", {}) or {}).get("mean", 0.0) or 0.0), 4),
        "unsafe_release_rate": round(float(holdout_challenge.get("unsafe_release_rate", 0.0) or 0.0), 4),
        "mechanism_breakdown": deepcopy(holdout_challenge.get("mechanism_breakdown", {})),
        "seed_reports": deepcopy(holdout_challenge.get("seed_reports", [])),
        "fraudgen_summary": fraudgen_summary(cases),
    }


def _blind_control_track_summary(public_benchmark: dict[str, Any]) -> dict[str, Any]:
    return {
        "track": BLIND_CONTROL_TRACK,
        "track_label": track_label(BLIND_CONTROL_TRACK),
        "track_mode": "blind",
        "case_count": int(public_benchmark.get("case_count", 0) or 0),
        "average_score": round(float(public_benchmark.get("average_score", 0.0) or 0.0), 4),
        "control_satisfied_resolution_rate": round(float(public_benchmark.get("control_satisfied_resolution_rate", 0.0) or 0.0), 4),
        "institutional_utility_mean": round(float((public_benchmark.get("institutional_utility_stats", {}) or {}).get("mean", 0.0) or 0.0), 4),
        "unsafe_release_rate": round(float(public_benchmark.get("unsafe_release_rate", 0.0) or 0.0), 4),
        "note": "Blind mode hides SPRT, VoI, and reward-machine scaffolding from the acting agent while preserving hidden grader state.",
    }


def _sleeper_vigilance_track_summary(controlbench_quarter: dict[str, Any]) -> dict[str, Any]:
    sleeper_rows = [
        row
        for row in controlbench_quarter.get("case_results", []) or []
        if normalize_text((row.get("controlbench", {}) or {}).get("sleeper_phase")) in {"warmup", "activation", "trust_building"}
    ]
    activation_rows = [
        row
        for row in sleeper_rows
        if normalize_text((row.get("controlbench", {}) or {}).get("sleeper_phase")) == "activation"
    ]
    return {
        "track": SLEEPER_VIGILANCE_TRACK,
        "track_label": track_label(SLEEPER_VIGILANCE_TRACK),
        "case_count": len(sleeper_rows),
        "activation_case_count": len(activation_rows),
        "sleeper_detection_rate": round(float(controlbench_quarter.get("sleeper_detection_rate", 0.0) or 0.0), 4),
        "unsafe_release_rate": round(
            sum(str(row.get("result_class")) == "unsafe_release" for row in activation_rows) / max(len(activation_rows), 1),
            4,
        ),
        "authority_restriction_rate": round(float(controlbench_quarter.get("authority_restriction_rate", 0.0) or 0.0), 4),
        "cases": sleeper_rows,
    }


def build_controlbench_artifact(report: dict[str, Any]) -> dict[str, Any]:
    controlbench = report.get("controlbench_quarter", {}) or {}
    protocol = report.get("evaluation_protocol", {}) or {}
    memory_after = controlbench.get("institutional_memory_after", {}) or {}
    ledger = memory_after.get("loss_ledger", {}) or {}
    gate = controlbench.get("calibration_gate", {}) or {}
    return {
        "benchmark": report.get("benchmark", "ledgershield-controlbench-v1"),
        "agent_name": protocol.get("model_name", DETERMINISTIC_BASELINE_MODEL),
        "agent_type": protocol.get("agent_type", "deterministic-policy"),
        "sequence_id": controlbench.get("sequence_id"),
        "sequence_seed": controlbench.get("sequence_seed"),
        "case_count": controlbench.get("sequence_length", 0),
        "standard_case_count": controlbench.get("standard_sequence_length", CONTROLBENCH_STANDARD_SEQUENCE_LENGTH),
        "preview_sequence": bool(controlbench.get("preview_sequence")),
        "accuracy": round(float(controlbench.get("accuracy", 0.0) or 0.0), 4),
        "average_case_score": round(float(controlbench.get("average_case_score", 0.0) or 0.0), 4),
        "fraud_recall": round(float(controlbench.get("fraud_recall", 0.0) or 0.0), 4),
        "false_positive_rate": round(float(controlbench.get("false_positive_rate", 0.0) or 0.0), 4),
        "unsafe_release_rate": round(float(controlbench.get("unsafe_release_rate", 0.0) or 0.0), 4),
        "institutional_loss_total": round(float(controlbench.get("institutional_loss_total", 0.0) or 0.0), 2),
        "institutional_loss_score": round(float(controlbench.get("institutional_loss_score", 0.0) or 0.0), 4),
        "loss_surface": deepcopy(controlbench.get("loss_surface", {})),
        "certificate_validity_rate": round(float(controlbench.get("certificate_validity_rate", 0.0) or 0.0), 4),
        "calibration_score": round(float(controlbench.get("calibration_score", 0.0) or 0.0), 4),
        "brier_score": round(float(controlbench.get("brier_score", 0.0) or 0.0), 4),
        "authority_level": gate.get("authority_level", memory_after.get("authority_level")),
        "authority_timeline": deepcopy(controlbench.get("authority_timeline", [])),
        "authority_restriction_rate": round(float(controlbench.get("authority_restriction_rate", 0.0) or 0.0), 4),
        "authority_restriction_count": int(ledger.get("authority_restriction_count", 0) or 0),
        "falsifier_block_rate": round(float(controlbench.get("falsifier_block_rate", 0.0) or 0.0), 4),
        "trust_graph_support_rate": round(float(controlbench.get("trust_graph_support_rate", 0.0) or 0.0), 4),
        "sleeper_detection_rate": round(float(controlbench.get("sleeper_detection_rate", 0.0) or 0.0), 4),
        "sleeper_activation_count": int(controlbench.get("sleeper_activation_count", 0) or 0),
        "catastrophic_events": int(controlbench.get("catastrophic_event_count", 0) or 0),
        "deployability_rating": controlbench.get("deployability_rating", "unknown"),
        "accuracy_loss_disagreement": round(float(controlbench.get("accuracy_loss_disagreement", 0.0) or 0.0), 4),
        "control_profile": {
            "institutional_value_preserved": round(float(controlbench.get("institutional_loss_score", 0.0) or 0.0), 4),
            "authority_status": gate.get("authority_level", memory_after.get("authority_level")),
            "certificate_validity_rate": round(float(controlbench.get("certificate_validity_rate", 0.0) or 0.0), 4),
            "sleeper_detection_rate": round(float(controlbench.get("sleeper_detection_rate", 0.0) or 0.0), 4),
        },
        "fraudgen_summary": deepcopy(controlbench.get("fraudgen_summary", {})),
        "generated_at": report.get("generated_at"),
    }


def _case_amount(case: dict[str, Any]) -> float:
    fields = (case.get("gold", {}) or {}).get("fields", {}) or {}
    try:
        return max(1.0, float(fields.get("total", 1.0) or 1.0))
    except (TypeError, ValueError):
        return 1.0


def _direct_outcome_for_policy(case: dict[str, Any], decision: str) -> dict[str, Any]:
    risky = bool((case.get("gold", {}) or {}).get("unsafe_if_pay"))
    amount = _case_amount(case)
    if decision == "PAY" and risky:
        return {
            "outcome_type": "unsafe_payment_released",
            "unsafe_payment": True,
            "portfolio_metrics": {"fraud_loss_released": amount},
        }
    if decision == "PAY":
        return {"outcome_type": "safe_payment_cleared", "unsafe_payment": False, "portfolio_metrics": {}}
    if risky:
        return {
            "outcome_type": "fraud_prevented",
            "unsafe_payment": False,
            "portfolio_metrics": {"fraud_loss_prevented": amount, "manual_review_minutes": 12.0, "operational_delay_hours": 2.0},
        }
    return {
        "outcome_type": "false_positive_operational_delay",
        "unsafe_payment": False,
        "portfolio_metrics": {"manual_review_minutes": 18.0, "operational_delay_hours": 5.0, "supplier_friction": 0.22},
    }


def _simulate_controlbench_policy(cases: list[dict[str, Any]], *, policy_name: str) -> dict[str, Any]:
    memory = InstitutionalMemory.from_cases(cases)
    rows: list[dict[str, Any]] = []
    correct_count = 0
    for index, case in enumerate(cases, start=1):
        gold = case.get("gold", {}) or {}
        risky = bool(gold.get("unsafe_if_pay"))
        controlbench = case.get("controlbench", {}) or {}
        sleeper_activation = controlbench.get("sleeper_phase") == "activation"
        if policy_name == "accuracy_optimized_agent":
            decision = "PAY" if (not risky or sleeper_activation) else "ESCALATE_FRAUD"
            confidence = 0.94
        elif policy_name == "control_optimized_agent":
            decision = "ESCALATE_FRAUD" if risky else ("NEEDS_REVIEW" if index % 11 == 0 else "PAY")
            confidence = 0.82 if risky else 0.76
        elif policy_name == "always_pay_agent":
            decision = "PAY"
            confidence = 0.90
        else:
            decision = "ESCALATE_FRAUD"
            confidence = 0.72
        correct = normalize_text(decision) == normalize_text(gold.get("decision")) if gold.get("decision") else True
        correct_count += int(correct)
        outcome = _direct_outcome_for_policy(case, decision)
        trajectory = [{"action_type": "request_callback_verification"}] if decision != "PAY" and risky else []
        record_institutional_outcome(
            memory,
            case=case,
            submitted={"decision": decision, "confidence": confidence},
            outcome=outcome,
            trajectory=trajectory,
            compliance={},
        )
        snapshot = public_institutional_memory(memory)
        rows.append(
            {
                "case_id": case.get("case_id"),
                "sequence_index": controlbench.get("sequence_index", index),
                "decision": decision,
                "correct": correct,
                "unsafe_payment": bool(outcome.get("unsafe_payment")),
                "authority_level": snapshot.get("authority_level"),
                "institutional_loss_score": (snapshot.get("loss_ledger", {}) or {}).get("institutional_loss_score"),
            }
        )
    snapshot = public_institutional_memory(memory)
    ledger = snapshot.get("loss_ledger", {}) or {}
    return {
        "agent_name": policy_name,
        "accuracy": round(correct_count / max(len(cases), 1), 4),
        "institutional_loss_score": float(ledger.get("institutional_loss_score", 0.0) or 0.0),
        "fraud_loss_released": float(ledger.get("fraud_loss_released", 0.0) or 0.0),
        "false_positive_cost": float(ledger.get("false_positive_cost", 0.0) or 0.0),
        "catastrophic_event_count": int(ledger.get("catastrophic_event_count", 0) or 0),
        "sleeper_detection_rate": float((snapshot.get("controlbench_summary", {}) or {}).get("sleeper_detection_rate", 0.0) or 0.0),
        "final_authority_level": snapshot.get("authority_level"),
        "deployability_rating": _deployability_rating(snapshot),
        "loss_surface": ledger.get("loss_surface", {}),
        "authority_timeline": rows,
    }


def _controlbench_two_agent_demo(cases: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = [
        _simulate_controlbench_policy(cases, policy_name="accuracy_optimized_agent"),
        _simulate_controlbench_policy(cases, policy_name="control_optimized_agent"),
        _simulate_controlbench_policy(cases, policy_name="always_pay_agent"),
        _simulate_controlbench_policy(cases, policy_name="always_escalate_agent"),
    ]
    profiles_by_name = {profile["agent_name"]: profile for profile in profiles}
    agent_a = profiles_by_name["accuracy_optimized_agent"]
    agent_b = profiles_by_name["control_optimized_agent"]
    return {
        "thesis": "Per-case accuracy can disagree with institutional deployability.",
        "sequence_length": len(cases),
        "profiles": profiles,
        "accuracy_loss_disagreement": round(
            abs(float(agent_a["accuracy"]) - float(agent_b["accuracy"]))
            + abs(float(agent_a["institutional_loss_score"]) - float(agent_b["institutional_loss_score"])),
            4,
        ),
        "punchline": "Traditional accuracy can prefer a riskier agent; ControlBench ranks by institutional loss, authority, and sleeper vigilance.",
    }


def _task_score_mean(section: dict[str, Any], task_type: str) -> float | None:
    task_breakdown = section.get("task_breakdown", {}) or {}
    task_summary = task_breakdown.get(task_type, {}) or {}
    score_stats = task_summary.get("score_stats", {}) or {}
    raw = score_stats.get("mean")
    if raw is None:
        return None
    return round(float(raw), 4)


def _evaluate_cases(
    cases: list[dict[str, Any]],
    *,
    base_db: dict[str, Any],
    client: Any = None,
    temperature: float = DEFAULT_TEMPERATURE,
    pass_k: int = DEFAULT_PASS_K,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> dict[str, Any]:
    db = _db_with_cases(base_db, cases)
    case_ids = [str(case["case_id"]) for case in cases if case.get("case_id")]
    evaluation = inference.run_local_baseline(
        case_ids,
        db=db,
        client=client,
        emit_logs=False,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )
    evaluation["results"] = _annotate_results(list(evaluation.get("results", [])), cases)
    return evaluation


def _approved_bank_account(case: dict[str, Any], vendors_by_key: dict[str, dict[str, Any]]) -> str | None:
    candidate_keys = {
        normalize_text(case.get("vendor_key")),
        normalize_text((case.get("gold", {}) or {}).get("vendor_key")),
    }
    for doc in case.get("documents", []) or []:
        candidate_keys.add(normalize_text(doc.get("vendor_key")))
    for candidate in candidate_keys:
        if candidate and candidate in vendors_by_key:
            account = str(vendors_by_key[candidate].get("bank_account", "")).strip()
            if account:
                return account
    return None


def _evaluate_contrastive_pairs(
    *,
    base_db: dict[str, Any],
    client: Any = None,
    temperature: float = DEFAULT_TEMPERATURE,
    pass_k: int = DEFAULT_PASS_K,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> dict[str, Any]:
    source_cases = _risky_contrastive_source_cases(base_db)
    pair_reports: list[dict[str, Any]] = []
    joint_scores: list[float] = []

    for index, adversarial_case in enumerate(source_cases):
        twin = generate_benign_twin(
            adversarial_case,
            seed=3100 + index,
            approved_bank_account=_approved_bank_account(adversarial_case, base_db.get("vendors_by_key", {})),
        )
        pair_eval = _evaluate_cases(
            [adversarial_case, twin],
            base_db=base_db,
            client=client,
            temperature=temperature,
            pass_k=pass_k,
            pass_threshold=pass_threshold,
        )
        results_by_id = {
            str(result.get("case_id")): result
            for result in pair_eval.get("results", [])
        }
        adversarial_result = results_by_id.get(str(adversarial_case.get("case_id")), {})
        twin_result = results_by_id.get(str(twin.get("case_id")), {})
        joint = evaluate_contrastive_pair(
            float(adversarial_result.get("score", 0.0) or 0.0),
            float(twin_result.get("score", 0.0) or 0.0),
            str(adversarial_result.get("final_decision", "")),
            str(twin_result.get("final_decision", "")),
        )
        joint_scores.append(float(joint.get("joint_score", 0.0) or 0.0))
        pair_reports.append(
            {
                "pair_id": adversarial_case.get("case_id"),
                "adversarial_case_id": adversarial_case.get("case_id"),
                "twin_case_id": twin.get("case_id"),
                "adversarial": adversarial_result,
                "twin": twin_result,
                "joint": joint,
            }
        )

    return {
        "pair_count": len(pair_reports),
        "joint_score_stats": _stats(joint_scores),
        "pair_reports": pair_reports,
    }


def _certificate_required_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for case in cases:
        cloned = deepcopy(case)
        cloned["case_id"] = f"{case['case_id']}::certificate-required"
        cloned["benchmark_split"] = "certificate_required"
        cloned["certificate_required"] = True
        tracks = set(cloned.get("official_tracks", []) or [])
        tracks.add(CERTIFICATE_REQUIRED_TRACK)
        cloned["official_tracks"] = sorted(tracks)
        cloned["primary_track"] = CERTIFICATE_REQUIRED_TRACK
        cloned.setdefault("generator_metadata", {})["certificate_required"] = True
        output.append(cloned)
    return output


def _evaluate_certificate_required_track(
    *,
    public_cases: list[dict[str, Any]],
    base_db: dict[str, Any],
    client: Any = None,
    temperature: float = DEFAULT_TEMPERATURE,
    pass_k: int = DEFAULT_PASS_K,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> dict[str, Any]:
    cases = _certificate_required_cases(public_cases)
    evaluation = _evaluate_cases(
        cases,
        base_db=base_db,
        client=client,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )
    summary = _section_summary(evaluation, pass_threshold=pass_threshold)
    missing_rate = round(
        sum(str((row.get("score_breakdown", {}) or {}).get("result_class")) == "certificate_required_missing" for row in summary.get("results", []))
        / max(len(summary.get("results", [])), 1),
        4,
    )
    return {
        "track": CERTIFICATE_REQUIRED_TRACK,
        "track_label": track_label(CERTIFICATE_REQUIRED_TRACK),
        "certificate_required_missing_rate": missing_rate,
        **summary,
    }


def _section_summary(section: dict[str, Any], *, pass_threshold: float) -> dict[str, Any]:
    results = list(section.get("results", []))
    metrics = _aggregate_result_metrics(results, pass_threshold)
    return {
        "case_count": len(results),
        "average_score": round(float(section.get("average_score", 0.0) or 0.0), 4),
        **metrics,
        "task_breakdown": _group_by_task(results, pass_threshold),
        "track_breakdown": _group_by_key(results, pass_threshold, key_name="benchmark_track", value_fn=lambda row: row.get("benchmark_track", "unknown")),
        "mechanism_breakdown": _group_by_key(results, pass_threshold, key_name="mechanism_family", value_fn=lambda row: row.get("mechanism_family", "unknown")),
        "risk_breakdown": _group_by_key(results, pass_threshold, key_name="unsafe_if_pay", value_fn=lambda row: "risky" if row.get("unsafe_if_pay") else "clean"),
        "control_type_breakdown": _group_by_key(results, pass_threshold, key_name="control_type", value_fn=lambda row: row.get("control_type", "unknown")),
        "split_breakdown": _group_by_key(results, pass_threshold, key_name="benchmark_split", value_fn=lambda row: row.get("benchmark_split", "benchmark")),
        "results": results,
    }


def _report_identity(*, model_name: str = "", client: Any = None) -> tuple[str, str]:
    if client is None:
        return DETERMINISTIC_BASELINE_MODEL, "deterministic-policy"
    return model_name or inference.MODEL_NAME, "llm-agent"


def build_report(
    *,
    holdout_seeds: list[int] | None = None,
    variants_per_case: int = 1,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    pass_k: int = DEFAULT_PASS_K,
    temperature: float = DEFAULT_TEMPERATURE,
    client: Any = None,
    model_name: str = "",
    controlbench_sequence_length: int = DEFAULT_CONTROLBENCH_SEQUENCE_LENGTH,
) -> dict[str, Any]:
    base_db = load_all()
    resolved_model_name, agent_type = _report_identity(model_name=model_name, client=client)
    public_cases = _benchmark_cases(base_db)
    public_eval = _evaluate_cases(
        public_cases,
        base_db=base_db,
        client=client,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )

    seed_reports: list[dict[str, Any]] = []
    all_holdout_results: list[dict[str, Any]] = []
    all_holdout_cases: list[dict[str, Any]] = []
    seeds = holdout_seeds or list(DEFAULT_HOLDOUT_SEEDS)

    for seed in seeds:
        holdout_cases = generate_holdout_suite(
            _hard_benchmark_cases(base_db),
            variants_per_case=variants_per_case,
            seed=seed,
        )
        holdout_eval = _evaluate_cases(
            holdout_cases,
            base_db=base_db,
            client=client,
            temperature=temperature,
            pass_k=pass_k,
            pass_threshold=pass_threshold,
        )
        all_holdout_cases.extend(deepcopy(case) for case in holdout_cases)
        holdout_results = list(holdout_eval.get("results", []))
        holdout_scores = [float(row.get("score", 0.0) or 0.0) for row in holdout_results]
        seed_reports.append(
            {
                "seed": seed,
                "case_count": len(holdout_cases),
                "average_score": round(float(holdout_eval.get("average_score", 0.0) or 0.0), 4),
                "score_stats": _stats(holdout_scores),
                "trial_pass_rate": round(float(holdout_eval.get("trial_pass_rate", 0.0) or 0.0), 4),
                "consistent_pass_rate": round(float(holdout_eval.get("consistent_pass_rate", 0.0) or 0.0), 4),
                "any_pass_rate": round(float(holdout_eval.get("any_pass_rate", 0.0) or 0.0), 4),
                "fraudgen_summary": fraudgen_summary(holdout_cases),
                "results": holdout_results,
            }
        )
        all_holdout_results.extend(holdout_results)

    holdout_scores = [float(row.get("score", 0.0) or 0.0) for row in all_holdout_results]
    holdout_trial_pass_rates = [float(row.get("trial_pass_rate", 0.0) or 0.0) for row in all_holdout_results]
    holdout_consistent = [bool(row.get("pass_k_consistent", False)) for row in all_holdout_results]
    holdout_any = [bool(row.get("pass_k_any", False)) for row in all_holdout_results]
    holdout_seed_averages = [float(batch.get("average_score", 0.0) or 0.0) for batch in seed_reports]
    public_benchmark = _section_summary(public_eval, pass_threshold=pass_threshold)
    holdout_challenge = {
        "seed_count": len(seed_reports),
        "variants_per_case": variants_per_case,
        "total_case_count": len(all_holdout_results),
        **_aggregate_result_metrics(all_holdout_results, pass_threshold),
        "suite_average_stats": _stats(holdout_seed_averages),
        "task_breakdown": _group_by_task(all_holdout_results, pass_threshold),
        "track_breakdown": _group_by_key(all_holdout_results, pass_threshold, key_name="benchmark_track", value_fn=lambda row: row.get("benchmark_track", "unknown")),
        "mechanism_breakdown": _group_by_key(all_holdout_results, pass_threshold, key_name="mechanism_family", value_fn=lambda row: row.get("mechanism_family", "unknown")),
        "split_breakdown": _group_by_key(all_holdout_results, pass_threshold, key_name="benchmark_split", value_fn=lambda row: row.get("benchmark_split", "holdout")),
        "seed_reports": seed_reports,
    }
    contrastive = _evaluate_contrastive_pairs(
        base_db=base_db,
        client=client,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )
    case_track_cases = [deepcopy(case) for case in public_cases if case_matches_track(case, CASE_TRACK)]
    adversarial_track_cases = [deepcopy(case) for case in public_cases if case_matches_track(case, ADVERSARIAL_DATA_TRACK)]
    official_tracks = {
        "case_track": {
            "track": CASE_TRACK,
            "track_label": track_label(CASE_TRACK),
            **_section_summary(
                _evaluate_cases(
                    case_track_cases,
                    base_db=base_db,
                    client=client,
                    temperature=temperature,
                    pass_k=pass_k,
                    pass_threshold=pass_threshold,
                ),
                pass_threshold=pass_threshold,
            ),
        },
        "adversarial_data_track": {
            "track": ADVERSARIAL_DATA_TRACK,
            "track_label": track_label(ADVERSARIAL_DATA_TRACK),
            **_section_summary(
                _evaluate_cases(
                    adversarial_track_cases,
                    base_db=base_db,
                    client=client,
                    temperature=temperature,
                    pass_k=pass_k,
                    pass_threshold=pass_threshold,
                ),
                pass_threshold=pass_threshold,
            ),
        },
        "portfolio_track": _evaluate_portfolio_sequences(
            base_db=base_db,
            client=client,
            temperature=temperature,
        ),
    }
    controlbench_quarter = _evaluate_controlbench_sequence(
        base_db=base_db,
        sequence_length=controlbench_sequence_length,
        seed=2026,
        client=client,
        temperature=temperature,
    )
    controlbench_demo_cases = generate_controlbench_sequence(
        _benchmark_cases(base_db),
        sequence_length=CONTROLBENCH_STANDARD_SEQUENCE_LENGTH,
        seed=2026,
    )
    two_agent_demo = _controlbench_two_agent_demo(controlbench_demo_cases)
    generated_holdout_track = _generated_holdout_track_summary(holdout_challenge, cases=all_holdout_cases)
    blind_control_track = _blind_control_track_summary(public_benchmark)
    sleeper_vigilance_track = _sleeper_vigilance_track_summary(controlbench_quarter)
    certificate_required_track = _evaluate_certificate_required_track(
        public_cases=public_cases,
        base_db=base_db,
        client=client,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )
    human_baseline_track = load_human_baseline_summary()
    official_tracks["controlbench_track"] = {
        "track": CONTROLBENCH_TRACK,
        "track_label": track_label(CONTROLBENCH_TRACK),
        "sequence_length": controlbench_quarter["sequence_length"],
        "institutional_loss_score": controlbench_quarter["institutional_loss_score"],
        "deployability_rating": controlbench_quarter["deployability_rating"],
        "sleeper_detection_rate": controlbench_quarter["sleeper_detection_rate"],
        "catastrophic_event_count": controlbench_quarter["catastrophic_event_count"],
    }
    official_tracks["generated_holdout_track"] = generated_holdout_track
    official_tracks["blind_control_track"] = blind_control_track
    official_tracks["sleeper_vigilance_track"] = sleeper_vigilance_track
    official_tracks["certificate_required_track"] = certificate_required_track
    official_tracks["human_baseline_track"] = human_baseline_track

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "benchmark": "ledgershield-controlbench-v1",
        "benchmark_identity": "Verified institutional control intelligence in enterprise AP workflows",
        "primary_theme": "World Modeling — Professional Tasks",
        "secondary_theme": "Long-Horizon Planning & Instruction Following",
        "generated_at": generated_at,
        "public_benchmark": public_benchmark,
        "holdout_challenge": holdout_challenge,
        "generated_holdout_track": generated_holdout_track,
        "blind_control_track": blind_control_track,
        "contrastive_pairs": contrastive,
        "controlbench_quarter": controlbench_quarter,
        "sleeper_vigilance_track": sleeper_vigilance_track,
        "controlbench_report": build_controlbench_artifact(
            {
                "benchmark": "ledgershield-controlbench-v1",
                "generated_at": generated_at,
                "controlbench_quarter": controlbench_quarter,
                "evaluation_protocol": {
                    "model_name": resolved_model_name,
                    "agent_type": agent_type,
                },
            }
        ),
        "controlbench_two_agent_demo": two_agent_demo,
        "certificate_required_track": certificate_required_track,
        "human_baseline_track": human_baseline_track,
        "fraudgen_summary": {
            "generated_holdout": fraudgen_summary(all_holdout_cases),
            "controlbench": deepcopy(controlbench_quarter.get("fraudgen_summary", {})),
        },
        "official_tracks": official_tracks,
        "evaluation_protocol": {
            "pass_threshold": round(float(pass_threshold), 4),
            "pass_k": int(pass_k),
            "temperature": round(float(temperature), 4),
            "holdout_seeds": seeds,
            "controlbench_sequence_length": int(controlbench_sequence_length),
            "controlbench_standard_sequence_length": CONTROLBENCH_STANDARD_SEQUENCE_LENGTH,
            "model_name": resolved_model_name,
            "agent_type": agent_type,
            "track_mode": "blind",
            "pass_k_definition": (
                "A case is counted as pass^k-consistent only if all k repeated trials "
                "score at or above the pass threshold."
            ),
        },
    }


def build_leaderboard_entry(
    report: dict[str, Any],
    *,
    model_name: str,
    agent_type: str,
) -> dict[str, Any]:
    public = report["public_benchmark"]
    holdout = report["holdout_challenge"]
    contrastive = report["contrastive_pairs"]
    controlbench = report.get("controlbench_quarter", {}) or {}
    certificate_track = report.get("certificate_required_track", {}) or {}
    two_agent_demo = report.get("controlbench_two_agent_demo", {}) or {}
    certificate_track = report.get("certificate_required_track", {}) or {}
    protocol = report["evaluation_protocol"]
    public_task_e_mean = _task_score_mean(public, "task_e")
    holdout_task_e_mean = _task_score_mean(holdout, "task_e")

    return {
        "model": model_name,
        "type": agent_type,
        "temperature": protocol["temperature"],
        "pass_k": protocol["pass_k"],
        "pass_threshold": protocol["pass_threshold"],
        "public_mean": public["average_score"],
        "public_control_satisfied_resolution": public["control_satisfied_resolution_rate"],
        "public_institutional_utility": public["institutional_utility_stats"]["mean"],
        "public_unsafe_release_rate": public["unsafe_release_rate"],
        "public_trial_pass_rate": public["trial_pass_rate"],
        "public_pass_k_consistent": public["consistent_pass_rate"],
        "holdout_mean": holdout["score_stats"]["mean"],
        "holdout_control_satisfied_resolution": holdout["control_satisfied_resolution_rate"],
        "holdout_institutional_utility": holdout["institutional_utility_stats"]["mean"],
        "holdout_unsafe_release_rate": holdout["unsafe_release_rate"],
        "holdout_trial_pass_rate": holdout["trial_pass_rate"],
        "holdout_pass_k_consistent": holdout["consistent_pass_rate"],
        "contrastive_joint_mean": contrastive["joint_score_stats"]["mean"],
        "controlbench_accuracy": round(float(controlbench.get("accuracy", 0.0) or 0.0), 4),
        "controlbench_fraud_recall": round(float(controlbench.get("fraud_recall", 0.0) or 0.0), 4),
        "controlbench_certificate_validity_rate": round(float(controlbench.get("certificate_validity_rate", 0.0) or 0.0), 4),
        "controlbench_institutional_loss_score": round(float(controlbench.get("institutional_loss_score", 0.0) or 0.0), 4),
        "controlbench_institutional_loss_total": round(float(controlbench.get("institutional_loss_total", 0.0) or 0.0), 2),
        "controlbench_deployability_rating": controlbench.get("deployability_rating", "unknown"),
        "controlbench_sleeper_detection_rate": round(float(controlbench.get("sleeper_detection_rate", 0.0) or 0.0), 4),
        "controlbench_catastrophic_event_count": int(controlbench.get("catastrophic_event_count", 0) or 0),
        "certificate_required_mean": round(float(certificate_track.get("average_score", 0.0) or 0.0), 4),
        "certificate_required_missing_rate": round(float(certificate_track.get("certificate_required_missing_rate", 0.0) or 0.0), 4),
        "public_task_e_expert_mean": public_task_e_mean,
        "holdout_task_e_expert_mean": holdout_task_e_mean,
        "task_e_expert_mean": holdout_task_e_mean if holdout_task_e_mean is not None else public_task_e_mean,
        "provenance": "generated-from-report",
        "updated_at": report["generated_at"],
    }


def _float_field(entry: dict[str, Any], field: str, default: float = 0.0) -> float:
    try:
        return float(entry.get(field, default) or default)
    except (TypeError, ValueError):
        return default


def _int_field(entry: dict[str, Any], field: str, default: int = 0) -> int:
    try:
        return int(entry.get(field, default) or default)
    except (TypeError, ValueError):
        return default


def _looks_like_llm_model_name(model_name: str) -> bool:
    lowered = normalize_text(model_name)
    llm_prefixes = (
        "gpt-",
        "openai/",
        "openai:",
        "claude",
        "anthropic/",
        "gemini",
        "google/",
        "meta-llama/",
        "llama-",
        "mistral",
        "deepseek",
        "qwen",
    )
    return any(lowered.startswith(prefix) for prefix in llm_prefixes)


def _is_legacy_deterministic_alias(existing: dict[str, Any], canonical: dict[str, Any]) -> bool:
    if str(canonical.get("model")) != DETERMINISTIC_BASELINE_MODEL:
        return False
    if str(canonical.get("type")) != "deterministic-policy":
        return False
    if str(existing.get("type")) != "deterministic-policy":
        return False
    if str(existing.get("model")) == DETERMINISTIC_BASELINE_MODEL:
        return False
    if str(existing.get("provenance")) != "generated-from-report":
        return False
    if _int_field(existing, "pass_k", 1) != _int_field(canonical, "pass_k", 1):
        return False
    if not math.isclose(
        _float_field(existing, "temperature"),
        _float_field(canonical, "temperature"),
        abs_tol=1e-9,
    ):
        return False
    return _looks_like_llm_model_name(str(existing.get("model", "")))


def _dedupe_leaderboard_entries(entries: list[dict[str, Any]], canonical: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, float, int]] = set()
    for entry in entries:
        if canonical is not None and _is_legacy_deterministic_alias(entry, canonical):
            continue
        key = (
            str(entry.get("model", "")),
            str(entry.get("type", "")),
            _float_field(entry, "temperature"),
            _int_field(entry, "pass_k", 1),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(entry)
    deduped.sort(
        key=lambda row: (
            _float_field(row, "holdout_pass_k_consistent"),
            _float_field(row, "holdout_mean"),
            _float_field(row, "public_mean"),
        ),
        reverse=True,
    )
    return deduped


def load_leaderboard_payload(
    *,
    leaderboard_path: Path = DEFAULT_LEADERBOARD_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    report: dict[str, Any] | None = None
    canonical_entry: dict[str, Any] | None = None
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        canonical_entry = build_leaderboard_entry(
            report,
            model_name=report.get("evaluation_protocol", {}).get("model_name", DETERMINISTIC_BASELINE_MODEL),
            agent_type=report.get("evaluation_protocol", {}).get("agent_type", "deterministic-policy"),
        )

    if leaderboard_path.exists():
        payload = json.loads(leaderboard_path.read_text(encoding="utf-8"))
        entries = _dedupe_leaderboard_entries(list(payload.get("entries", [])), canonical=canonical_entry)
        if entries != list(payload.get("entries", [])):
            payload = {
                **payload,
                "entries": entries,
            }
        return payload

    if report is not None:
        entry = build_leaderboard_entry(
            report,
            model_name=report.get("evaluation_protocol", {}).get("model_name", "ledgershield-baseline-v2"),
            agent_type=report.get("evaluation_protocol", {}).get("agent_type", "deterministic-policy"),
        )
        return {
            "benchmark": report.get("benchmark", "ledgershield-controlbench-v1"),
            "generated_at": report.get("generated_at"),
            "entries": [entry],
            "note": "Leaderboard artifact not found; derived from latest benchmark report artifact.",
        }

    return {
        "benchmark": "ledgershield-controlbench-v1",
        "generated_at": None,
        "entries": [],
        "note": "No leaderboard artifact generated yet. Run benchmark_report.py to create one.",
    }


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def upsert_leaderboard_entry(
    entry: dict[str, Any],
    *,
    leaderboard_path: Path = DEFAULT_LEADERBOARD_PATH,
) -> dict[str, Any]:
    payload = load_leaderboard_payload(leaderboard_path=leaderboard_path, report_path=DEFAULT_REPORT_PATH)
    entries = list(payload.get("entries", []))
    retained = [
        existing
        for existing in entries
        if not (
            str(existing.get("model")) == str(entry.get("model"))
            and str(existing.get("type")) == str(entry.get("type"))
            and _float_field(existing, "temperature") == _float_field(entry, "temperature")
            and _int_field(existing, "pass_k", 1) == _int_field(entry, "pass_k", 1)
        )
    ]
    retained.append(entry)
    retained = _dedupe_leaderboard_entries(retained, canonical=entry)
    updated = {
        "benchmark": "ledgershield-controlbench-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": retained,
        "note": (
            "pass_k_consistent is the fraction of benchmark cases that remained above the pass threshold "
            "on all repeated trials. task_e_expert_mean is the holdout mean for the expert multi-invoice "
            "campaign task when that task is present in the evaluated suite."
        ),
    }
    write_json_artifact(leaderboard_path, updated)
    return updated


def _format_markdown(report: dict[str, Any]) -> str:
    public = report["public_benchmark"]
    holdout = report["holdout_challenge"]
    contrastive = report["contrastive_pairs"]
    controlbench = report.get("controlbench_quarter", {}) or {}
    certificate_track = report.get("certificate_required_track", {}) or {}
    two_agent_demo = report.get("controlbench_two_agent_demo", {}) or {}
    official_tracks = report.get("official_tracks", {}) or {}
    protocol = report["evaluation_protocol"]
    public_task_e_mean = _task_score_mean(public, "task_e")
    holdout_task_e_mean = _task_score_mean(holdout, "task_e")
    public_lines = [
        "# LedgerShield Benchmark Report",
        "",
        f"Benchmark identity: {report.get('benchmark_identity', '')}",
        f"Primary theme: {report.get('primary_theme', '')}",
        f"Secondary theme: {report.get('secondary_theme', '')}",
        "",
        "## Evaluation Protocol",
        f"- Model: {protocol['model_name']}",
        f"- Agent type: {protocol['agent_type']}",
        f"- Observation mode: {protocol.get('track_mode', 'blind')}",
        f"- Temperature: {protocol['temperature']:.2f}",
        f"- pass^k trials: {protocol['pass_k']}",
        f"- Pass threshold: {protocol['pass_threshold']:.2f}",
        f"- ControlBench sequence length: {protocol.get('controlbench_sequence_length', 0)} "
        f"(standard {protocol.get('controlbench_standard_sequence_length', CONTROLBENCH_STANDARD_SEQUENCE_LENGTH)})",
        "",
        "## Public Benchmark",
        f"- Cases: {public['case_count']}",
        f"- Average score: {public['average_score']:.4f}",
        f"- Control-Satisfied Resolution: {public['control_satisfied_resolution_rate']:.4f}",
        f"- Institutional Utility: {public['institutional_utility_stats']['mean']:.4f}",
        f"- Unsafe release rate: {public['unsafe_release_rate']:.4f}",
        f"- Pass rate @ {protocol['pass_threshold']:.2f}: {public['pass_rate']:.4f}",
        f"- Trial pass rate: {public['trial_pass_rate']:.4f}",
        f"- pass^{protocol['pass_k']} consistent rate: {public['consistent_pass_rate']:.4f}",
        f"- Score stddev: {public['score_stats']['stdev']:.4f}",
    ]
    if public_task_e_mean is not None:
        public_lines.append(f"- Task E expert mean: {public_task_e_mean:.4f}")

    holdout_lines = [
        "",
        "## Holdout Challenge",
        f"- Holdout seeds: {', '.join(str(seed) for seed in protocol['holdout_seeds'])}",
        f"- Variants per hard case: {holdout['variants_per_case']}",
        f"- Total holdout cases: {holdout['total_case_count']}",
        f"- Mean score: {holdout['score_stats']['mean']:.4f}",
        f"- Control-Satisfied Resolution: {holdout['control_satisfied_resolution_rate']:.4f}",
        f"- Institutional Utility: {holdout['institutional_utility_stats']['mean']:.4f}",
        f"- Unsafe release rate: {holdout['unsafe_release_rate']:.4f}",
        f"- Pass rate @ {protocol['pass_threshold']:.2f}: {holdout['pass_rate']:.4f}",
        f"- Trial pass rate: {holdout['trial_pass_rate']:.4f}",
        f"- pass^{protocol['pass_k']} consistent rate: {holdout['consistent_pass_rate']:.4f}",
        f"- Any-pass rate over {protocol['pass_k']} trials: {holdout['any_pass_rate']:.4f}",
        f"- Seed-average stddev: {holdout['suite_average_stats']['stdev']:.4f}",
    ]
    if holdout_task_e_mean is not None:
        holdout_lines.append(f"- Task E expert mean: {holdout_task_e_mean:.4f}")

    lines = public_lines + holdout_lines + [
        "",
        "## Contrastive Calibration",
        f"- Adversarial/twin pairs: {contrastive['pair_count']}",
        f"- Joint score mean: {contrastive['joint_score_stats']['mean']:.4f}",
        f"- Joint score stddev: {contrastive['joint_score_stats']['stdev']:.4f}",
        "",
        "## ControlBench Institutional Sequence",
        f"- Sequence length: {controlbench.get('sequence_length', 0)}",
        f"- Accuracy: {float(controlbench.get('accuracy', 0.0) or 0.0):.4f}",
        f"- Fraud recall: {float(controlbench.get('fraud_recall', 0.0) or 0.0):.4f}",
        f"- False-positive rate: {float(controlbench.get('false_positive_rate', 0.0) or 0.0):.4f}",
        f"- Institutional loss score: {float(controlbench.get('institutional_loss_score', 0.0) or 0.0):.4f}",
        f"- Institutional loss total: {float(controlbench.get('institutional_loss_total', 0.0) or 0.0):.2f}",
        f"- Deployability rating: {controlbench.get('deployability_rating', 'unknown')}",
        f"- Certificate validity rate: {float(controlbench.get('certificate_validity_rate', 0.0) or 0.0):.4f}",
        f"- Authority restriction rate: {float(controlbench.get('authority_restriction_rate', 0.0) or 0.0):.4f}",
        f"- Sleeper detection rate: {float(controlbench.get('sleeper_detection_rate', 0.0) or 0.0):.4f}",
        f"- Catastrophic events: {int(controlbench.get('catastrophic_event_count', 0) or 0)}",
        f"- Accuracy/loss disagreement: {float(controlbench.get('accuracy_loss_disagreement', 0.0) or 0.0):.4f}",
        "",
        "## Certificate-Required Track",
        f"- Mean score: {float(certificate_track.get('average_score', 0.0) or 0.0):.4f}",
        f"- Missing agent-authored certificate rate: {float(certificate_track.get('certificate_required_missing_rate', 0.0) or 0.0):.4f}",
        "",
        "## Two-Agent Control Profile",
        f"- Thesis: {two_agent_demo.get('thesis', '')}",
        f"- Accuracy/loss disagreement: {float(two_agent_demo.get('accuracy_loss_disagreement', 0.0) or 0.0):.4f}",
        f"- Punchline: {two_agent_demo.get('punchline', '')}",
    ]
    if official_tracks:
        lines.extend(
            [
                "",
                "## Official Tracks",
                f"- Case Track CSR: {official_tracks.get('case_track', {}).get('control_satisfied_resolution_rate', 0.0):.4f}",
                f"- Adversarial Data Track unsafe release rate: {official_tracks.get('adversarial_data_track', {}).get('unsafe_release_rate', 0.0):.4f}",
                f"- Portfolio Track institutional utility: {official_tracks.get('portfolio_track', {}).get('institutional_utility_stats', {}).get('mean', 0.0):.4f}",
                f"- Generated Holdout Track mean: {official_tracks.get('generated_holdout_track', {}).get('average_score', 0.0):.4f}",
                f"- ControlBench Track loss score: {official_tracks.get('controlbench_track', {}).get('institutional_loss_score', 0.0):.4f}",
                f"- Sleeper-Vigilance Track detection rate: {official_tracks.get('sleeper_vigilance_track', {}).get('sleeper_detection_rate', 0.0):.4f}",
                f"- Blind-Control Track mean: {official_tracks.get('blind_control_track', {}).get('average_score', 0.0):.4f}",
                f"- Certificate-Required Track mean: {official_tracks.get('certificate_required_track', {}).get('average_score', 0.0):.4f}",
                f"- Human-Baseline Track accuracy: {official_tracks.get('human_baseline_track', {}).get('accuracy', 0.0):.4f}",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LedgerShield benchmark report")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--variants-per-case", type=int, default=1)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument("--holdout-seeds", nargs="*", type=int, default=DEFAULT_HOLDOUT_SEEDS)
    parser.add_argument("--pass-k", type=int, default=DEFAULT_PASS_K)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--controlbench-sequence-length", type=int, default=DEFAULT_CONTROLBENCH_SEQUENCE_LENGTH)
    parser.add_argument("--api-url", default=inference.API_BASE_URL)
    parser.add_argument("--model", default=inference.MODEL_NAME)
    parser.add_argument("--token", default=inference.HF_TOKEN)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))
    parser.add_argument("--controlbench-report-path", default=str(DEFAULT_CONTROLBENCH_REPORT_PATH))
    parser.add_argument("--skip-write", action="store_true")
    parser.add_argument("--skip-leaderboard", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inference.API_BASE_URL = args.api_url
    inference.MODEL_NAME = args.model
    inference.HF_TOKEN = args.token
    client = inference.build_openai_client()

    report = build_report(
        holdout_seeds=list(args.holdout_seeds),
        variants_per_case=int(args.variants_per_case),
        pass_threshold=float(args.pass_threshold),
        pass_k=max(1, int(args.pass_k)),
        temperature=float(args.temperature),
        client=client,
        model_name=args.model,
        controlbench_sequence_length=max(1, int(args.controlbench_sequence_length)),
    )

    if not args.skip_write:
        report_path = Path(args.report_path)
        write_json_artifact(report_path, report)
        write_json_artifact(Path(args.controlbench_report_path), report.get("controlbench_report", {}))

    if not args.skip_leaderboard:
        resolved_model_name, agent_type = _report_identity(model_name=args.model, client=client)
        leaderboard_entry = build_leaderboard_entry(
            report,
            model_name=resolved_model_name,
            agent_type=agent_type,
        )
        upsert_leaderboard_entry(leaderboard_entry, leaderboard_path=Path(args.leaderboard_path))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(_format_markdown(report))


if __name__ == "__main__":
    main()
