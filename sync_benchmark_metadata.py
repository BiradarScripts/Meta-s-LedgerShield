from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import inference
from server.data_loader import load_all


ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
INDEX_DOC_PATH = ROOT / "docs" / "index.md"
API_DOC_PATH = ROOT / "docs" / "api-reference.md"
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
    lines = [
        "## Live Comparison Snapshot",
        "",
        f"Generated on **{generated_on}** from `live_model_comparison.json`.",
        "",
    ]
    if include_capability:
        lines.extend(
            [
                "| Model | Tier | Capability | Average Score | Success Rate | Min Score | Max Score | API Calls |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in _comparison_rows(payload):
            profile = row.get("model_profile", {}) or {}
            lines.append(
                "| "
                f"`{row.get('model', '')}` | "
                f"{profile.get('tier', '')} | "
                f"{float(profile.get('capability_score', 0.0)):.1f} | "
                f"{float(row.get('average_score', 0.0)):.4f} | "
                f"{100.0 * float(row.get('success_rate', 0.0)):.1f}% | "
                f"{float(row.get('min_score', 0.0)):.2f} | "
                f"{float(row.get('max_score', 0.0)):.2f} | "
                f"{int(row.get('api_calls', 0) or 0)} |"
            )
    else:
        lines.extend(
            [
                "| Model | Average Score | Success Rate | Failed Cases |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in _comparison_rows(payload):
            lines.append(
                "| "
                f"`{row.get('model', '')}` | "
                f"{float(row.get('average_score', 0.0)):.4f} | "
                f"{100.0 * float(row.get('success_rate', 0.0)):.1f}% | "
                f"{len(row.get('failed_cases', []) or [])} |"
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


def sync_readme() -> None:
    counts = _loader_counts()
    payload = _load_live_comparison()
    content = _read(README_PATH)
    content = _replace_once(
        content,
        r"^\| Default loader behavior \| .+ \|$",
        f"| Default loader behavior | {counts['benchmark']} benchmark cases + {counts['challenge']} generated challenge variants = {counts['total']} loaded cases |",
    )
    content = _replace_block(
        content,
        "<!-- sync:readme-capability-table:start -->",
        "<!-- sync:readme-capability-table:end -->",
        _capability_table("Budget bonus"),
    )
    content = _replace_block(
        content,
        "<!-- sync:readme-live-comparison:start -->",
        "<!-- sync:readme-live-comparison:end -->",
        _comparison_block(payload, include_capability=True),
    )
    _write(README_PATH, content)


def sync_index_doc() -> None:
    counts = _loader_counts()
    payload = _load_live_comparison()
    content = _read(INDEX_DOC_PATH)
    content = _replace_once(
        content,
        r"With the current loader defaults, `load_all\(\)` produces \*\*\d+ total cases\*\* locally:",
        f"With the current loader defaults, `load_all()` produces **{counts['total']} total cases** locally:",
    )
    content = _replace_once(
        content,
        r"- \d+ benchmark cases",
        f"- {counts['benchmark']} benchmark cases",
    )
    content = _replace_once(
        content,
        r"- \d+ generated challenge variants",
        f"- {counts['challenge']} generated challenge variants",
    )
    content = _replace_block(
        content,
        "<!-- sync:index-capability-table:start -->",
        "<!-- sync:index-capability-table:end -->",
        _capability_table("Budget bonus"),
    )
    content = _replace_block(
        content,
        "<!-- sync:index-live-comparison:start -->",
        "<!-- sync:index-live-comparison:end -->",
        _comparison_block(payload, include_capability=False),
    )
    _write(INDEX_DOC_PATH, content)


def sync_api_doc() -> None:
    content = _read(API_DOC_PATH)
    content = _replace_block(
        content,
        "<!-- sync:api-capability-table:start -->",
        "<!-- sync:api-capability-table:end -->",
        _capability_table("Decision token budget"),
    )
    _write(API_DOC_PATH, content)


def sync_openenv() -> None:
    counts = _loader_counts()
    content = _read(OPENENV_PATH)
    content = _replace_once(
        content,
        r"^  challenge_variants_default: \d+$",
        f"  challenge_variants_default: {counts['challenge']}",
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
