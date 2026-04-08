#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MODELS = ["gpt-4o", "gpt-5.4"]
DEFAULT_CASES = [
    "CASE-A-001",
    "CASE-A-002",
    "CASE-A-003",
    "CASE-A-004",
    "CASE-B-001",
    "CASE-B-002",
    "CASE-B-003",
    "CASE-B-004",
    "CASE-B-005",
    "CASE-C-001",
    "CASE-C-002",
    "CASE-C-003",
    "CASE-C-004",
    "CASE-D-001",
    "CASE-D-002",
    "CASE-D-003",
    "CASE-D-004",
    "CASE-D-005",
    "CASE-D-006",
    "CASE-E-001",
    "CASE-E-002",
]
PASS_THRESHOLD = 0.85
DEFAULT_TIMEOUT_SECONDS = 1200

START_RE = re.compile(r"^\[START\]\s+task=(\S+)\s+env=(\S+)\s+model=(\S+)\s*$")
END_RE = re.compile(
    r"^\[END\]\s+success=(true|false)\s+steps=(\d+)\s+(?:score=([0-9]+\.[0-9]+)\s+)?rewards=(.*)\s*$"
)
API_CALLS_RE = re.compile(r"^Total API calls:\s*(\d+)\s*$")


@dataclass
class ModelStats:
    model: str
    average_score: float
    success_rate: float
    min_score: float
    max_score: float
    failed_cases: list[str]
    case_scores: dict[str, float]
    api_calls: int
    debug_artifact_dir: str = ""
    model_profile: dict[str, Any] = field(default_factory=dict)


def _model_dirname(model: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", model.strip())
    return cleaned or "model"


def _score_from_end(score_field: str | None, rewards_field: str) -> float:
    if score_field:
        try:
            return float(score_field)
        except ValueError:
            pass
    parts = [p.strip() for p in rewards_field.split(",") if p.strip()]
    if not parts:
        return 0.0
    try:
        return float(parts[-1])
    except ValueError:
        return 0.0


def _base_model_score(model_name: str) -> float:
    normalized = re.sub(r"\s+", " ", model_name.strip().lower())
    if "gpt-4o" in normalized:
        base = 4.6
    else:
        match = re.search(r"gpt-([0-9]+(?:\.[0-9]+)?)", normalized)
        if match:
            base = float(match.group(1))
        elif "gpt-4" in normalized:
            base = 4.0
        elif "gpt-3.5" in normalized:
            base = 3.5
        else:
            base = 4.0

    if "pro" in normalized:
        base += 0.5
    if "latest" in normalized:
        base += 0.2
    if "mini" in normalized:
        base -= 0.7
    if "nano" in normalized:
        base -= 1.1
    if "turbo" in normalized:
        base -= 0.3
    return base


def _fallback_model_profile(model_name: str) -> dict[str, Any]:
    score = _base_model_score(model_name)
    if score >= 5.0:
        return {
            "model_name": model_name,
            "capability_score": score,
            "tier": "elite",
            "plan_mode": "coverage",
            "repair_level": "grounded",
            "investigation_budget_bonus": 2,
            "intervention_budget_bonus": 2,
            "decision_token_budget": 1536,
            "planning_token_budget": 640,
        }
    if score >= 4.5:
        return {
            "model_name": model_name,
            "capability_score": score,
            "tier": "strong",
            "plan_mode": "hybrid",
            "repair_level": "partial",
            "investigation_budget_bonus": 1,
            "intervention_budget_bonus": 1,
            "decision_token_budget": 1280,
            "planning_token_budget": 512,
        }
    return {
        "model_name": model_name,
        "capability_score": score,
        "tier": "standard",
        "plan_mode": "llm",
        "repair_level": "none",
        "investigation_budget_bonus": 0,
        "intervention_budget_bonus": 0,
        "decision_token_budget": 1024,
        "planning_token_budget": 384,
    }


def _model_profile_for(model_name: str) -> dict[str, Any]:
    try:
        from inference_llm_powered import get_model_capability_profile

        return asdict(get_model_capability_profile(model_name))
    except Exception:
        return _fallback_model_profile(model_name)


def _load_model_profile_from_debug_artifacts(debug_artifact_dir: Path | None) -> dict[str, Any]:
    if debug_artifact_dir is None or not debug_artifact_dir.exists():
        return {}
    for artifact_path in sorted(debug_artifact_dir.glob("*.json")):
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        profile = payload.get("model_profile")
        if isinstance(profile, dict) and profile:
            return profile
    return {}


def _display_path(path: Path | None) -> str:
    if path is None:
        return ""
    return path.as_posix()


def _capability_score(stats: ModelStats) -> float:
    value = stats.model_profile.get("capability_score", 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_capability_summary(results: list[ModelStats]) -> dict[str, Any]:
    ordered = sorted(results, key=lambda item: (_capability_score(item), item.model))
    ordered_models = [item.model for item in ordered]
    pairwise: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for weaker, stronger in zip(ordered, ordered[1:]):
        avg_gap = round(stronger.average_score - weaker.average_score, 4)
        success_gap = round(stronger.success_rate - weaker.success_rate, 4)
        ordering_ok = avg_gap >= 0.0 and success_gap >= 0.0
        comparison = {
            "weaker_model": weaker.model,
            "stronger_model": stronger.model,
            "weaker_tier": weaker.model_profile.get("tier", "unknown"),
            "stronger_tier": stronger.model_profile.get("tier", "unknown"),
            "average_score_gap": avg_gap,
            "success_rate_gap": success_gap,
            "ordering_ok": ordering_ok,
        }
        pairwise.append(comparison)
        if not ordering_ok:
            violations.append(comparison)

    return {
        "ordered_models": ordered_models,
        "monotonic_by_capability": not violations,
        "pairwise": pairwise,
        "violations": violations,
    }


def build_output_payload(
    results: list[ModelStats],
    *,
    cases: list[str],
    pass_threshold: float,
    api_base_url: str,
    env_url: str,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": [r.model for r in results],
        "cases": cases,
        "case_count": len(cases),
        "pass_threshold": pass_threshold,
        "runtime_context": {
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "api_base_url": api_base_url,
            "env_url": env_url,
        },
        "capability_order": build_capability_summary(results),
        "results": [
            {
                "model": r.model,
                "model_profile": r.model_profile,
                "average_score": round(r.average_score, 4),
                "success_rate": round(r.success_rate, 4),
                "min_score": round(r.min_score, 4),
                "max_score": round(r.max_score, 4),
                "api_calls": r.api_calls,
                "debug_artifact_dir": r.debug_artifact_dir,
                "failed_cases": r.failed_cases,
                "case_scores": {k: round(v, 4) for k, v in r.case_scores.items()},
            }
            for r in results
        ],
    }


def run_one_model(
    model: str,
    *,
    repo_root: Path,
    api_base_url: str,
    env_url: str,
    api_key: str,
    cases: list[str],
    timeout_seconds: int,
    pass_threshold: float,
    debug_artifact_dir: Path | None = None,
) -> ModelStats:
    env = os.environ.copy()
    env["MODEL_NAME"] = model
    env["API_BASE_URL"] = api_base_url
    env["ENV_URL"] = env_url
    env["OPENAI_API_KEY"] = api_key

    cmd = [sys.executable, "inference_llm_powered.py", "--cases", *cases]
    if debug_artifact_dir is not None:
        cmd.extend(["--debug-artifact-dir", str(debug_artifact_dir)])
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{model} run failed (exit {proc.returncode}):\n{proc.stderr}")

    current_case: str | None = None
    case_scores: dict[str, float] = {}
    api_calls = -1

    for raw_line in proc.stdout.splitlines():
        line = raw_line.strip()
        start_match = START_RE.match(line)
        if start_match:
            current_case = start_match.group(1)
            continue
        end_match = END_RE.match(line)
        if end_match and current_case:
            case_scores[current_case] = _score_from_end(end_match.group(3), end_match.group(4))
            current_case = None
            continue
        api_calls_match = API_CALLS_RE.match(line)
        if api_calls_match:
            api_calls = int(api_calls_match.group(1))

    if not case_scores:
        raise RuntimeError(f"{model} run did not produce parseable case scores.\nSTDOUT:\n{proc.stdout}")
    if api_calls == 0:
        raise RuntimeError(
            f"{model} produced 0 API calls. The run likely fell back to heuristic logic instead of live model inference."
        )

    scores = list(case_scores.values())
    avg_score = sum(scores) / len(scores)
    failed = [case for case, score in case_scores.items() if score < pass_threshold]
    success_rate = (len(scores) - len(failed)) / len(scores)
    model_profile = _load_model_profile_from_debug_artifacts(debug_artifact_dir) or _model_profile_for(model)

    return ModelStats(
        model=model,
        average_score=avg_score,
        success_rate=success_rate,
        min_score=min(scores),
        max_score=max(scores),
        failed_cases=failed,
        case_scores=case_scores,
        api_calls=api_calls,
        debug_artifact_dir=_display_path(debug_artifact_dir),
        model_profile=model_profile,
    )


def _fmt_failed(cases: list[str]) -> str:
    if not cases:
        return "0"
    labels = ", ".join(cases)
    return f"{len(cases)} ({labels})"


def print_table(results: list[ModelStats]) -> None:
    if not results:
        return

    metric_width = 18
    col_width = max(20, min(36, max(len(item.model) for item in results) + 6))

    def row(metric: str, values: list[str]) -> str:
        return f"{metric:<{metric_width}}" + "".join(f"{value:<{col_width}}" for value in values)

    print("\n" + "=" * (metric_width + col_width * len(results)))
    print(row("Metric", [item.model for item in results]))
    print("-" * (metric_width + col_width * len(results)))
    print(row("Tier", [str(item.model_profile.get("tier", "unknown")) for item in results]))
    print(row("Capability", [f"{_capability_score(item):.1f}" for item in results]))
    print(row("Average Score", [f"{item.average_score:.4f}" for item in results]))
    print(row("Success Rate", [f"{item.success_rate * 100:.1f}%" for item in results]))
    print(row("Min Score", [f"{item.min_score:.2f}" for item in results]))
    print(row("Max Score", [f"{item.max_score:.2f}" for item in results]))
    print(row("API Calls", [str(item.api_calls) for item in results]))
    print(row("Failed Cases", [_fmt_failed(item.failed_cases) for item in results]))
    print("=" * (metric_width + col_width * len(results)) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Live model-vs-model comparison for LedgerShield.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    parser.add_argument("--cases", default=",".join(DEFAULT_CASES), help="Comma-separated case ids.")
    parser.add_argument("--output", default="live_model_comparison.json", help="Output JSON path.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-model subprocess timeout for inference_llm_powered.py.",
    )
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    cases = [case.strip() for case in args.cases.split(",") if case.strip()]
    if len(models) < 2:
        print("Need at least 2 models in --models", file=sys.stderr)
        return 2
    if not cases:
        print("Need at least 1 case in --cases", file=sys.stderr)
        return 2

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    env_url = os.getenv("ENV_URL", "http://127.0.0.1:8000")
    repo_root = Path(__file__).resolve().parent
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    debug_root = out_path.with_name(f"{out_path.stem}_debug")

    results: list[ModelStats] = []
    for model in models:
        print(f"Running {model} ...")
        stats = run_one_model(
            model,
            repo_root=repo_root,
            api_base_url=api_base_url,
            env_url=env_url,
            api_key=api_key,
            cases=cases,
            timeout_seconds=args.timeout_seconds,
            pass_threshold=PASS_THRESHOLD,
            debug_artifact_dir=debug_root / _model_dirname(model),
        )
        results.append(stats)

    output_payload = build_output_payload(
        results,
        cases=cases,
        pass_threshold=PASS_THRESHOLD,
        api_base_url=api_base_url,
        env_url=env_url,
    )
    out_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    print_table(results)
    capability_summary = output_payload["capability_order"]
    print(
        "Capability ordering check:",
        "PASS" if capability_summary["monotonic_by_capability"] else "VIOLATION",
    )
    print(f"Saved detailed output to: {out_path}")
    print(f"Saved debug case traces to: {debug_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
