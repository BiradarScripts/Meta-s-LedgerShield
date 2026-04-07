from __future__ import annotations

import argparse
import json
import math
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import inference
from server.case_factory import generate_benign_twin, generate_holdout_suite
from server.data_loader import load_all
from server.grading import evaluate_contrastive_pair
from server.schema import normalize_text


DEFAULT_HOLDOUT_SEEDS = [2026, 2027, 2028]
DEFAULT_PASS_THRESHOLD = 0.85
DEFAULT_PASS_K = 1
DEFAULT_TEMPERATURE = 0.0
ARTIFACT_DIR = Path("artifacts")
DEFAULT_REPORT_PATH = ARTIFACT_DIR / "benchmark_report_latest.json"
DEFAULT_LEADERBOARD_PATH = ARTIFACT_DIR / "leaderboard.json"


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


def _group_by_task(results: list[dict[str, Any]], pass_threshold: float) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(str(result.get("task_type", "unknown")), []).append(result)

    summary: dict[str, Any] = {}
    for task_type, rows in sorted(grouped.items()):
        scores = [float(row.get("score", 0.0) or 0.0) for row in rows]
        trial_pass_rates = [float(row.get("trial_pass_rate", 0.0) or 0.0) for row in rows]
        consistent = [bool(row.get("pass_k_consistent", False)) for row in rows]
        any_pass = [bool(row.get("pass_k_any", False)) for row in rows]
        summary[task_type] = {
            "count": len(rows),
            "score_stats": _stats(scores),
            "pass_rate": round(sum(score >= pass_threshold for score in scores) / max(len(scores), 1), 4),
            "trial_pass_rate": round(sum(trial_pass_rates) / max(len(trial_pass_rates), 1), 4),
            "consistent_pass_rate": round(sum(consistent) / max(len(consistent), 1), 4),
            "any_pass_rate": round(sum(any_pass) / max(len(any_pass), 1), 4),
        }
    return summary


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
    return inference.run_local_baseline(
        case_ids,
        db=db,
        client=client,
        emit_logs=False,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )


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


def _section_summary(section: dict[str, Any], *, pass_threshold: float) -> dict[str, Any]:
    results = list(section.get("results", []))
    scores = [float(row.get("score", 0.0) or 0.0) for row in results]
    return {
        "case_count": len(results),
        "average_score": round(float(section.get("average_score", 0.0) or 0.0), 4),
        "score_stats": _stats(scores),
        "pass_rate": round(sum(score >= pass_threshold for score in scores) / max(len(scores), 1), 4),
        "trial_pass_rate": round(float(section.get("trial_pass_rate", 0.0) or 0.0), 4),
        "consistent_pass_rate": round(float(section.get("consistent_pass_rate", 0.0) or 0.0), 4),
        "any_pass_rate": round(float(section.get("any_pass_rate", 0.0) or 0.0), 4),
        "task_breakdown": _group_by_task(results, pass_threshold),
        "results": results,
    }


def build_report(
    *,
    holdout_seeds: list[int] | None = None,
    variants_per_case: int = 1,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    pass_k: int = DEFAULT_PASS_K,
    temperature: float = DEFAULT_TEMPERATURE,
    client: Any = None,
    model_name: str = "",
) -> dict[str, Any]:
    base_db = load_all()
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
                "results": holdout_results,
            }
        )
        all_holdout_results.extend(holdout_results)

    holdout_scores = [float(row.get("score", 0.0) or 0.0) for row in all_holdout_results]
    holdout_trial_pass_rates = [float(row.get("trial_pass_rate", 0.0) or 0.0) for row in all_holdout_results]
    holdout_consistent = [bool(row.get("pass_k_consistent", False)) for row in all_holdout_results]
    holdout_any = [bool(row.get("pass_k_any", False)) for row in all_holdout_results]
    holdout_seed_averages = [float(batch.get("average_score", 0.0) or 0.0) for batch in seed_reports]
    contrastive = _evaluate_contrastive_pairs(
        base_db=base_db,
        client=client,
        temperature=temperature,
        pass_k=pass_k,
        pass_threshold=pass_threshold,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "benchmark": "ledgershield-v3",
        "generated_at": generated_at,
        "public_benchmark": _section_summary(public_eval, pass_threshold=pass_threshold),
        "holdout_challenge": {
            "seed_count": len(seed_reports),
            "variants_per_case": variants_per_case,
            "total_case_count": len(all_holdout_results),
            "score_stats": _stats(holdout_scores),
            "pass_rate": round(sum(score >= pass_threshold for score in holdout_scores) / max(len(holdout_scores), 1), 4),
            "trial_pass_rate": round(sum(holdout_trial_pass_rates) / max(len(holdout_trial_pass_rates), 1), 4),
            "consistent_pass_rate": round(sum(holdout_consistent) / max(len(holdout_consistent), 1), 4),
            "any_pass_rate": round(sum(holdout_any) / max(len(holdout_any), 1), 4),
            "suite_average_stats": _stats(holdout_seed_averages),
            "task_breakdown": _group_by_task(all_holdout_results, pass_threshold),
            "seed_reports": seed_reports,
        },
        "contrastive_pairs": contrastive,
        "evaluation_protocol": {
            "pass_threshold": round(float(pass_threshold), 4),
            "pass_k": int(pass_k),
            "temperature": round(float(temperature), 4),
            "holdout_seeds": seeds,
            "model_name": model_name or inference.MODEL_NAME,
            "agent_type": "llm-agent" if client is not None else "deterministic-policy",
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
    protocol = report["evaluation_protocol"]

    return {
        "model": model_name,
        "type": agent_type,
        "temperature": protocol["temperature"],
        "pass_k": protocol["pass_k"],
        "pass_threshold": protocol["pass_threshold"],
        "public_mean": public["average_score"],
        "public_trial_pass_rate": public["trial_pass_rate"],
        "public_pass_k_consistent": public["consistent_pass_rate"],
        "holdout_mean": holdout["score_stats"]["mean"],
        "holdout_trial_pass_rate": holdout["trial_pass_rate"],
        "holdout_pass_k_consistent": holdout["consistent_pass_rate"],
        "contrastive_joint_mean": contrastive["joint_score_stats"]["mean"],
        "updated_at": report["generated_at"],
    }


def load_leaderboard_payload(
    *,
    leaderboard_path: Path = DEFAULT_LEADERBOARD_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    if leaderboard_path.exists():
        return json.loads(leaderboard_path.read_text(encoding="utf-8"))

    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        entry = build_leaderboard_entry(
            report,
            model_name=report.get("evaluation_protocol", {}).get("model_name", "ledgershield-baseline-v3"),
            agent_type=report.get("evaluation_protocol", {}).get("agent_type", "deterministic-policy"),
        )
        return {
            "benchmark": report.get("benchmark", "ledgershield-v3"),
            "generated_at": report.get("generated_at"),
            "entries": [entry],
            "note": "Leaderboard artifact not found; derived from latest benchmark report artifact.",
        }

    return {
        "benchmark": "ledgershield-v3",
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
            and float(existing.get("temperature", 0.0) or 0.0) == float(entry.get("temperature", 0.0) or 0.0)
            and int(existing.get("pass_k", 1) or 1) == int(entry.get("pass_k", 1) or 1)
        )
    ]
    retained.append(entry)
    retained.sort(key=lambda row: (float(row.get("holdout_pass_k_consistent", 0.0) or 0.0), float(row.get("holdout_mean", 0.0) or 0.0)), reverse=True)
    updated = {
        "benchmark": "ledgershield-v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": retained,
        "note": (
            "pass_k_consistent is the fraction of benchmark cases that remained above the pass threshold "
            "on all repeated trials."
        ),
    }
    write_json_artifact(leaderboard_path, updated)
    return updated


def _format_markdown(report: dict[str, Any]) -> str:
    public = report["public_benchmark"]
    holdout = report["holdout_challenge"]
    contrastive = report["contrastive_pairs"]
    protocol = report["evaluation_protocol"]

    lines = [
        "# LedgerShield Benchmark Report",
        "",
        "## Evaluation Protocol",
        f"- Model: {protocol['model_name']}",
        f"- Agent type: {protocol['agent_type']}",
        f"- Temperature: {protocol['temperature']:.2f}",
        f"- pass^k trials: {protocol['pass_k']}",
        f"- Pass threshold: {protocol['pass_threshold']:.2f}",
        "",
        "## Public Benchmark",
        f"- Cases: {public['case_count']}",
        f"- Average score: {public['average_score']:.4f}",
        f"- Pass rate @ {protocol['pass_threshold']:.2f}: {public['pass_rate']:.4f}",
        f"- Trial pass rate: {public['trial_pass_rate']:.4f}",
        f"- pass^{protocol['pass_k']} consistent rate: {public['consistent_pass_rate']:.4f}",
        f"- Score stddev: {public['score_stats']['stdev']:.4f}",
        "",
        "## Holdout Challenge",
        f"- Holdout seeds: {', '.join(str(seed) for seed in protocol['holdout_seeds'])}",
        f"- Variants per hard case: {holdout['variants_per_case']}",
        f"- Total holdout cases: {holdout['total_case_count']}",
        f"- Mean score: {holdout['score_stats']['mean']:.4f}",
        f"- Pass rate @ {protocol['pass_threshold']:.2f}: {holdout['pass_rate']:.4f}",
        f"- Trial pass rate: {holdout['trial_pass_rate']:.4f}",
        f"- pass^{protocol['pass_k']} consistent rate: {holdout['consistent_pass_rate']:.4f}",
        f"- Any-pass rate over {protocol['pass_k']} trials: {holdout['any_pass_rate']:.4f}",
        f"- Seed-average stddev: {holdout['suite_average_stats']['stdev']:.4f}",
        "",
        "## Contrastive Calibration",
        f"- Adversarial/twin pairs: {contrastive['pair_count']}",
        f"- Joint score mean: {contrastive['joint_score_stats']['mean']:.4f}",
        f"- Joint score stddev: {contrastive['joint_score_stats']['stdev']:.4f}",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LedgerShield benchmark report")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--variants-per-case", type=int, default=1)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument("--holdout-seeds", nargs="*", type=int, default=DEFAULT_HOLDOUT_SEEDS)
    parser.add_argument("--pass-k", type=int, default=DEFAULT_PASS_K)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--api-url", default=inference.API_BASE_URL)
    parser.add_argument("--model", default=inference.MODEL_NAME)
    parser.add_argument("--token", default=inference.API_KEY)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))
    parser.add_argument("--skip-write", action="store_true")
    parser.add_argument("--skip-leaderboard", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inference.API_BASE_URL = args.api_url
    inference.MODEL_NAME = args.model
    inference.API_KEY = args.token
    client = inference.build_openai_client()

    report = build_report(
        holdout_seeds=list(args.holdout_seeds),
        variants_per_case=int(args.variants_per_case),
        pass_threshold=float(args.pass_threshold),
        pass_k=max(1, int(args.pass_k)),
        temperature=float(args.temperature),
        client=client,
        model_name=args.model,
    )

    if not args.skip_write:
        report_path = Path(args.report_path)
        write_json_artifact(report_path, report)

    if not args.skip_leaderboard:
        leaderboard_entry = build_leaderboard_entry(
            report,
            model_name=args.model,
            agent_type="llm-agent" if client is not None else "deterministic-policy",
        )
        upsert_leaderboard_entry(leaderboard_entry, leaderboard_path=Path(args.leaderboard_path))

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(_format_markdown(report))


if __name__ == "__main__":
    main()
