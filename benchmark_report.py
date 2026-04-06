from __future__ import annotations

import argparse
import json
import math
import statistics
from copy import deepcopy
from typing import Any

import inference
from server.case_factory import generate_holdout_suite
from server.data_loader import load_all
from server.schema import normalize_text


DEFAULT_HOLDOUT_SEEDS = [2026, 2027, 2028]
DEFAULT_PASS_THRESHOLD = 0.85


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
        if normalize_text(case.get("task_type")) in {"task_c", "task_d"}
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


def _group_by_task(results: list[dict[str, Any]], pass_threshold: float) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(str(result.get("task_type", "unknown")), []).append(result)

    summary: dict[str, Any] = {}
    for task_type, rows in sorted(grouped.items()):
        scores = [float(row.get("score", 0.0) or 0.0) for row in rows]
        pass_rate = sum(score >= pass_threshold for score in scores) / max(len(scores), 1)
        summary[task_type] = {
            "count": len(rows),
            "score_stats": _stats(scores),
            "pass_rate": round(pass_rate, 4),
        }
    return summary


def _evaluate_cases(cases: list[dict[str, Any]], base_db: dict[str, Any]) -> dict[str, Any]:
    db = _db_with_cases(base_db, cases)
    case_ids = [str(case["case_id"]) for case in cases if case.get("case_id")]
    return inference.run_local_baseline(case_ids, db=db, client=None, emit_logs=False)


def _pass_k(pass_rate: float, k: int) -> float:
    return round(1.0 - ((1.0 - pass_rate) ** k), 4)


def build_report(
    *,
    holdout_seeds: list[int] | None = None,
    variants_per_case: int = 1,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> dict[str, Any]:
    base_db = load_all()
    public_cases = _benchmark_cases(base_db)
    public_eval = _evaluate_cases(public_cases, base_db)
    public_results = list(public_eval.get("results", []))
    public_scores = [float(row.get("score", 0.0) or 0.0) for row in public_results]
    public_pass_rate = sum(score >= pass_threshold for score in public_scores) / max(len(public_scores), 1)

    seed_reports: list[dict[str, Any]] = []
    all_holdout_results: list[dict[str, Any]] = []
    seeds = holdout_seeds or list(DEFAULT_HOLDOUT_SEEDS)

    for seed in seeds:
        holdout_cases = generate_holdout_suite(
            _hard_benchmark_cases(base_db),
            variants_per_case=variants_per_case,
            seed=seed,
        )
        holdout_eval = _evaluate_cases(holdout_cases, base_db)
        holdout_results = list(holdout_eval.get("results", []))
        holdout_scores = [float(row.get("score", 0.0) or 0.0) for row in holdout_results]
        holdout_pass_rate = sum(score >= pass_threshold for score in holdout_scores) / max(len(holdout_scores), 1)
        seed_reports.append(
            {
                "seed": seed,
                "case_count": len(holdout_cases),
                "average_score": round(float(holdout_eval.get("average_score", 0.0) or 0.0), 4),
                "score_stats": _stats(holdout_scores),
                "pass_rate": round(holdout_pass_rate, 4),
                "results": holdout_results,
            }
        )
        all_holdout_results.extend(holdout_results)

    holdout_scores = [float(row.get("score", 0.0) or 0.0) for row in all_holdout_results]
    holdout_pass_rate = sum(score >= pass_threshold for score in holdout_scores) / max(len(holdout_scores), 1)
    holdout_seed_averages = [float(batch.get("average_score", 0.0) or 0.0) for batch in seed_reports]

    return {
        "public_benchmark": {
            "case_count": len(public_cases),
            "average_score": round(float(public_eval.get("average_score", 0.0) or 0.0), 4),
            "score_stats": _stats(public_scores),
            "pass_rate": round(public_pass_rate, 4),
            "task_breakdown": _group_by_task(public_results, pass_threshold),
            "results": public_results,
        },
        "holdout_challenge": {
            "seed_count": len(seed_reports),
            "variants_per_case": variants_per_case,
            "total_case_count": len(all_holdout_results),
            "score_stats": _stats(holdout_scores),
            "pass_rate": round(holdout_pass_rate, 4),
            "pass_k": {
                "pass^1": _pass_k(holdout_pass_rate, 1),
                "pass^4": _pass_k(holdout_pass_rate, 4),
                "pass^8": _pass_k(holdout_pass_rate, 8),
            },
            "suite_average_stats": _stats(holdout_seed_averages),
            "task_breakdown": _group_by_task(all_holdout_results, pass_threshold),
            "seed_reports": seed_reports,
        },
        "report_config": {
            "pass_threshold": pass_threshold,
            "holdout_seeds": seeds,
        },
    }


def _format_markdown(report: dict[str, Any]) -> str:
    public = report["public_benchmark"]
    holdout = report["holdout_challenge"]
    config = report["report_config"]

    lines = [
        "# LedgerShield Benchmark Report",
        "",
        "## Public Benchmark",
        f"- Cases: {public['case_count']}",
        f"- Average score: {public['average_score']:.4f}",
        f"- Pass rate @ {config['pass_threshold']:.2f}: {public['pass_rate']:.4f}",
        f"- Score stddev: {public['score_stats']['stdev']:.4f}",
        "",
        "## Holdout Challenge",
        f"- Holdout seeds: {', '.join(str(seed) for seed in config['holdout_seeds'])}",
        f"- Variants per hard case: {holdout['variants_per_case']}",
        f"- Total holdout cases: {holdout['total_case_count']}",
        f"- Mean score: {holdout['score_stats']['mean']:.4f}",
        f"- Pass rate @ {config['pass_threshold']:.2f}: {holdout['pass_rate']:.4f}",
        f"- pass^1 / pass^4 / pass^8: {holdout['pass_k']['pass^1']:.4f} / {holdout['pass_k']['pass^4']:.4f} / {holdout['pass_k']['pass^8']:.4f}",
        f"- Seed-average stddev: {holdout['suite_average_stats']['stdev']:.4f}",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic LedgerShield benchmark report")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--variants-per-case", type=int, default=1)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument("--holdout-seeds", nargs="*", type=int, default=DEFAULT_HOLDOUT_SEEDS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        holdout_seeds=list(args.holdout_seeds),
        variants_per_case=int(args.variants_per_case),
        pass_threshold=float(args.pass_threshold),
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(_format_markdown(report))


if __name__ == "__main__":
    main()
