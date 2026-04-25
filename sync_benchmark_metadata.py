from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import benchmark_report
import inference
from server.data_loader import load_all


ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
INDEX_DOC_PATH = ROOT / "docs" / "DOCUMENTATION.md"
API_DOC_PATH = ROOT / "docs" / "DOCUMENTATION.md"
OPENENV_PATH = ROOT / "openenv.yaml"
LIVE_COMPARISON_PATH = ROOT / "live_model_comparison.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _replace_block(content: str, start_marker: str, end_marker: str, replacement: str) -> str:
    pattern = re.compile(
        rf"({re.escape(start_marker)}\n)(.*?)(\n{re.escape(end_marker)})",
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(rf"\1{replacement}\3", content, count=1)
    if count != 1:
        raise ValueError(f"Could not replace block between {start_marker!r} and {end_marker!r}")
    return updated


def _replace_once(content: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one replacement for pattern: {pattern}")
    return updated


def _replace_once_if_present(content: str, pattern: str, replacement: str) -> str:
    if re.search(pattern, content, flags=re.MULTILINE) is None:
        return content
    return _replace_once(content, pattern, replacement)


def _replace_block_if_present(content: str, start_marker: str, end_marker: str, replacement: str) -> str:
    marker_block = f"{start_marker}\n"
    if marker_block not in content or end_marker not in content:
        return content
    return _replace_block(content, start_marker, end_marker, replacement)


def _loader_counts() -> dict[str, int]:
    db = load_all()
    cases = list(db.get("cases", []))
    benchmark_cases = [
        case
        for case in cases
        if str(case.get("benchmark_split", "benchmark")).strip().lower() == "benchmark"
    ]
    challenge_cases = [
        case
        for case in cases
        if str(case.get("benchmark_split", "")).strip().lower() == "challenge"
    ]
    holdout_cases = [
        case
        for case in cases
        if str(case.get("benchmark_split", "")).strip().lower() == "holdout"
    ]
    contrastive_cases = [
        case
        for case in cases
        if str(case.get("benchmark_split", "")).strip().lower() == "contrastive"
    ]
    return {
        "benchmark": len(benchmark_cases),
        "challenge": len(challenge_cases),
        "holdout": len(holdout_cases),
        "contrastive": len(contrastive_cases),
        "total": len(cases),
    }


def _load_live_comparison() -> dict[str, Any]:
    return json.loads(_read(LIVE_COMPARISON_PATH))


def _load_report() -> dict[str, Any] | None:
    report_path = benchmark_report.DEFAULT_REPORT_PATH
    if not report_path.exists():
        return None
    return json.loads(_read(report_path))


def _generated_on_ist(payload: dict[str, Any]) -> str:
    raw = str(payload.get("generated_at_utc", "")).strip()
    if not raw:
        return "unknown date"
    dt = datetime.fromisoformat(raw)
    ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    return f"{ist.strftime('%B')} {ist.day}, {ist.year} (IST)"


def _comparison_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload.get("results", []))


def _capability_table(budget_column_name: str) -> str:
    elite = inference.get_model_capability_profile("gpt-5.4")
    strong = inference.get_model_capability_profile("gpt-4o")
    standard = inference.get_model_capability_profile("gpt-3.5-turbo")

    if budget_column_name == "Budget bonus":
        rows = [
            ("Elite", ">= 5.0", elite.plan_mode, elite.repair_level, f"+{elite.investigation_budget_bonus} investigation, +{elite.intervention_budget_bonus} intervention"),
            ("Strong", ">= 4.5", strong.plan_mode, strong.repair_level, f"+{strong.investigation_budget_bonus} investigation, +{strong.intervention_budget_bonus} intervention"),
            ("Standard", "< 4.5", standard.plan_mode, standard.repair_level, "baseline"),
        ]
    else:
        rows = [
            ("Elite", ">= 5.0", elite.plan_mode, elite.repair_level, f">= {elite.decision_token_budget}"),
            ("Strong", ">= 4.5", strong.plan_mode, strong.repair_level, f">= {strong.decision_token_budget}"),
            ("Standard", "< 4.5", standard.plan_mode, standard.repair_level, "model default"),
        ]

    lines = [
        f"| Tier | Capability score | Plan mode | Repair level | {budget_column_name} |",
        "|---|---|---|---|---|",
    ]
    for tier, score, plan_mode, repair_level, budget in rows:
        lines.append(f"| {tier} | {score} | `{plan_mode}` | `{repair_level}` | {budget} |")
    return "\n".join(lines)


def _comparison_block(payload: dict[str, Any], *, include_capability: bool) -> str:
    generated_on = _generated_on_ist(payload)
    rows = _comparison_rows(payload)
    has_audit_metrics = any(
        "average_certificate_score" in row or "average_institutional_loss_score" in row
        for row in rows
    )
    lines = [
        "## Live Comparison Snapshot",
        "",
        f"Generated on **{generated_on}** from `live_model_comparison.json`.",
        "",
    ]
    if include_capability:
        if has_audit_metrics:
            lines.extend(
                [
                    "| Model | Tier | Capability | Average Score | Success Rate | Certificate | Inst. Loss | Min Score | Max Score | API Calls |",
                    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                ]
            )
        else:
            lines.extend(
                [
                    "| Model | Tier | Capability | Average Score | Success Rate | Min Score | Max Score | API Calls |",
                    "|---|---|---:|---:|---:|---:|---:|---:|",
                ]
            )
        for row in rows:
            profile = row.get("model_profile", {}) or {}
            line = (
                "| "
                f"`{row.get('model', '')}` | "
                f"{profile.get('tier', '')} | "
                f"{float(profile.get('capability_score', 0.0)):.1f} | "
                f"{float(row.get('average_score', 0.0)):.4f} | "
                f"{100.0 * float(row.get('success_rate', 0.0)):.1f}% | "
            )
            if has_audit_metrics:
                line += (
                    f"{float(row.get('average_certificate_score', 0.0)):.4f} | "
                    f"{float(row.get('average_institutional_loss_score', 0.0)):.4f} | "
                )
            line += (
                f"{float(row.get('min_score', 0.0)):.2f} | "
                f"{float(row.get('max_score', 0.0)):.2f} | "
                f"{int(row.get('api_calls', 0) or 0)} |"
            )
            lines.append(line)
    else:
        if has_audit_metrics:
            lines.extend(
                [
                    "| Model | Average Score | Success Rate | Certificate | Inst. Loss | Failed Cases |",
                    "|---|---:|---:|---:|---:|---:|",
                ]
            )
        else:
            lines.extend(
                [
                    "| Model | Average Score | Success Rate | Failed Cases |",
                    "|---|---:|---:|---:|",
                ]
            )
        for row in rows:
            line = (
                "| "
                f"`{row.get('model', '')}` | "
                f"{float(row.get('average_score', 0.0)):.4f} | "
                f"{100.0 * float(row.get('success_rate', 0.0)):.1f}% | "
            )
            if has_audit_metrics:
                line += (
                    f"{float(row.get('average_certificate_score', 0.0)):.4f} | "
                    f"{float(row.get('average_institutional_loss_score', 0.0)):.4f} | "
                )
            line += f"{len(row.get('failed_cases', []) or [])} |"
            lines.append(line)

    if not has_audit_metrics:
        lines.extend(
            [
                "",
                "- Audit metrics are not present in this historical artifact. Rerun `compare_models_live.py` with the current code to populate certificate and institutional-loss columns.",
            ]
        )

    capability_order = payload.get("capability_order", {}) or {}
    pairwise = capability_order.get("pairwise", []) or []
    gpt4o_gap = next(
        (
            row
            for row in pairwise
            if row.get("weaker_model") == "gpt-4o" and row.get("stronger_model") == "gpt-5.4"
        ),
        None,
    )
    if gpt4o_gap is not None:
        lines.extend(
            [
                "",
                f"- Capability ordering is monotonic across the compared models: `{str(bool(capability_order.get('monotonic_by_capability', False))).lower()}`.",
                f"- Current frontier gap (`gpt-5.4` vs `gpt-4o`): `+{float(gpt4o_gap.get('average_score_gap', 0.0)):.4f}` average score and `+{100.0 * float(gpt4o_gap.get('success_rate_gap', 0.0)):.1f}%` success rate.",
                "- Refresh after rerunning the live comparison artifact:",
                "```bash",
                "python compare_models_live.py \\",
                "  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \\",
                "  --output live_model_comparison.json",
                "python sync_benchmark_metadata.py",
                "```",
            ]
        )

    return "\n".join(lines)


def _benchmark_summary_block(report: dict[str, Any]) -> str:
    protocol = report.get("evaluation_protocol", {}) or {}
    public = report.get("public_benchmark", {}) or {}
    holdout = report.get("holdout_challenge", {}) or {}
    controlbench = report.get("controlbench_quarter", {}) or {}
    certificate_track = report.get("certificate_required_track", {}) or {}
    lines = [
        "| Agent | Public mean | Holdout mean | Holdout consistent pass rate | ControlBench loss score | Deployability | Certificate-required mean |",
        "|---|---:|---:|---:|---:|---|---:|",
        (
            "| "
            f"{protocol.get('model_name', benchmark_report.DETERMINISTIC_BASELINE_MODEL)} "
            f"({protocol.get('agent_type', 'deterministic-policy')}) | "
            f"{float(public.get('average_score', 0.0)):.4f} | "
            f"{float((holdout.get('score_stats', {}) or {}).get('mean', 0.0)):.4f} | "
            f"{float(holdout.get('consistent_pass_rate', 0.0) or 0.0):.4f} | "
            f"{float(controlbench.get('institutional_loss_score', 0.0) or 0.0):.4f} | "
            f"{controlbench.get('deployability_rating', 'unknown')} | "
            f"{float(certificate_track.get('average_score', 0.0) or 0.0):.4f} |"
        ),
    ]
    return "\n".join(lines)


def _leaderboard_example_block(report: dict[str, Any]) -> str:
    entry = benchmark_report.build_leaderboard_entry(
        report,
        model_name=str((report.get("evaluation_protocol", {}) or {}).get("model_name", benchmark_report.DETERMINISTIC_BASELINE_MODEL)),
        agent_type=str((report.get("evaluation_protocol", {}) or {}).get("agent_type", "deterministic-policy")),
    )
    snippet = {
        "benchmark": report.get("benchmark", "ledgershield-controlbench-v1"),
        "generated_at": report.get("generated_at"),
        "entries": [
            {
                "model": entry["model"],
                "type": entry["type"],
                "public_mean": entry["public_mean"],
                "holdout_mean": entry["holdout_mean"],
                "holdout_pass_k_consistent": entry["holdout_pass_k_consistent"],
                "controlbench_institutional_loss_score": entry.get("controlbench_institutional_loss_score", 0.0),
                "controlbench_deployability_rating": entry.get("controlbench_deployability_rating", "unknown"),
                "certificate_required_mean": entry.get("certificate_required_mean", 0.0),
            }
        ],
    }
    return json.dumps(snippet, indent=2)


def sync_readme() -> None:
    counts = _loader_counts()
    payload = _load_live_comparison()
    report = _load_report()
    content = _read(README_PATH)
    content = _replace_once_if_present(
        content,
        r"^\| Default loader behavior \| .+ \|$",
        f"| Default loader behavior | {counts['benchmark']} benchmark cases + {counts['challenge']} generated challenge variants = {counts['total']} loaded cases |",
    )
    content = _replace_block_if_present(
        content,
        "<!-- sync:readme-capability-table:start -->",
        "<!-- sync:readme-capability-table:end -->",
        _capability_table("Budget bonus"),
    )
    content = _replace_block_if_present(
        content,
        "<!-- sync:readme-live-comparison:start -->",
        "<!-- sync:readme-live-comparison:end -->",
        _comparison_block(payload, include_capability=True),
    )
    if report is not None:
        content = _replace_block_if_present(
            content,
            "<!-- sync:readme-benchmark-summary:start -->",
            "<!-- sync:readme-benchmark-summary:end -->",
            _benchmark_summary_block(report),
        )
    _write(README_PATH, content)


def sync_index_doc() -> None:
    counts = _loader_counts()
    payload = _load_live_comparison()
    content = _read(INDEX_DOC_PATH)
    content = _replace_once_if_present(
        content,
        r"With the current loader defaults, `load_all\(\)` produces \*\*\d+ total cases\*\* locally:",
        f"With the current loader defaults, `load_all()` produces **{counts['total']} total cases** locally:",
    )
    content = _replace_once_if_present(
        content,
        r"- \d+ benchmark cases",
        f"- {counts['benchmark']} benchmark cases",
    )
    content = _replace_once_if_present(
        content,
        r"- \d+ generated challenge variants",
        f"- {counts['challenge']} generated challenge variants",
    )
    content = _replace_block_if_present(
        content,
        "<!-- sync:index-capability-table:start -->",
        "<!-- sync:index-capability-table:end -->",
        _capability_table("Budget bonus"),
    )
    content = _replace_block_if_present(
        content,
        "<!-- sync:index-live-comparison:start -->",
        "<!-- sync:index-live-comparison:end -->",
        _comparison_block(payload, include_capability=False),
    )
    _write(INDEX_DOC_PATH, content)


def sync_api_doc() -> None:
    content = _read(API_DOC_PATH)
    content = _replace_block_if_present(
        content,
        "<!-- sync:api-capability-table:start -->",
        "<!-- sync:api-capability-table:end -->",
        _capability_table("Decision token budget"),
    )
    report = _load_report()
    if report is not None:
        content = _replace_block_if_present(
            content,
            "<!-- sync:api-leaderboard-example:start -->",
            "<!-- sync:api-leaderboard-example:end -->",
            _leaderboard_example_block(report),
        )
    _write(API_DOC_PATH, content)


def sync_openenv() -> None:
    counts = _loader_counts()
    report = _load_report()
    content = _read(OPENENV_PATH)
    content = _replace_once(
        content,
        r"^  challenge_variants_default: \d+$",
        f"  challenge_variants_default: {counts['challenge']}",
    )
    if report is not None:
        protocol = report.get("evaluation_protocol", {}) or {}
        public = report.get("public_benchmark", {}) or {}
        holdout = report.get("holdout_challenge", {}) or {}
        controlbench = report.get("controlbench_quarter", {}) or {}
        certificate_track = report.get("certificate_required_track", {}) or {}
        task_breakdown = holdout.get("task_breakdown", {}) or {}
        task_e_summary = task_breakdown.get("task_e", {}) or {}
        task_e_mean = float((task_e_summary.get("score_stats", {}) or {}).get("mean", 0.0) or 0.0)
        benchmark_results_block = "\n".join(
            [
                "  benchmark_results:",
                "    deterministic_baseline:",
                f"      model: {protocol.get('model_name', benchmark_report.DETERMINISTIC_BASELINE_MODEL)}",
                f"      type: {protocol.get('agent_type', 'deterministic-policy')}",
                f"      temperature: {float(protocol.get('temperature', 0.0) or 0.0):.1f}",
                f"      pass_k: {int(protocol.get('pass_k', 1) or 1)}",
                f"      public_mean: {float(public.get('average_score', 0.0) or 0.0):.4f}",
                f"      holdout_mean: {float((holdout.get('score_stats', {}) or {}).get('mean', 0.0) or 0.0):.4f}",
                f"      holdout_pass_k_consistent: {float(holdout.get('consistent_pass_rate', 0.0) or 0.0):.4f}",
                f"      controlbench_institutional_loss_score: {float(controlbench.get('institutional_loss_score', 0.0) or 0.0):.4f}",
                f"      controlbench_deployability_rating: {controlbench.get('deployability_rating', 'unknown')}",
                f"      controlbench_sleeper_detection_rate: {float(controlbench.get('sleeper_detection_rate', 0.0) or 0.0):.4f}",
                f"      certificate_required_mean: {float(certificate_track.get('average_score', 0.0) or 0.0):.4f}",
                f"      task_e_expert_mean: {task_e_mean:.4f}",
                "      provenance: generated-from-benchmark-report",
            ]
        )
        content = _replace_once(
            content,
            r"(?ms)^  benchmark_results:\n.*\Z",
            benchmark_results_block,
        )
    _write(OPENENV_PATH, content)


def main() -> None:
    sync_readme()
    sync_index_doc()
    sync_api_doc()
    sync_openenv()
    print("Synchronized README, docs, and openenv metadata from current artifacts/code.")


if __name__ == "__main__":
    main()
