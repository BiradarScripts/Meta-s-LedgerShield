#!/usr/bin/env python3
"""
Comprehensive OpenAI Model Comparison for LedgerShield
Tests models from weak (GPT-3.5) to SOTA (GPT-5.4)
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

# Model tiers from weakest to strongest
MODEL_TIERS = [
    ("gpt-3.5-turbo", "Legacy/Weak"),
    ("gpt-4.1-nano", "Entry-level"),
    ("gpt-4.1-mini", "Budget"),
    ("gpt-4.1", "Mid-range"),
    ("gpt-4o", "Strong"),
    ("gpt-4o-latest", "Latest 4o"),
    ("gpt-5", "SOTA v1"),
    ("gpt-5-mini", "SOTA Mini"),
    ("gpt-5.4", "SOTA 5.4"),
    ("gpt-5.4-mini", "SOTA 5.4 Mini"),
    ("gpt-5.4-pro", "SOTA 5.4 Pro"),
]

REPO_ROOT = Path(__file__).resolve().parent
PASS_THRESHOLD = 0.85
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_OUTPUT_PATH = "comprehensive_model_comparison.json"
END_RE = re.compile(
    r"^\[END\]\s+success=(true|false)\s+steps=(\d+)\s+(?:score=([0-9]+\.[0-9]+)\s+)?rewards=(.*)\s*$"
)
API_CALLS_RE = re.compile(r"^Total API calls:\s*(\d+)\s*$")


def _score_from_end(score_field: str | None, rewards_field: str) -> float:
    if score_field:
        try:
            return float(score_field)
        except ValueError:
            pass
    parts = [part.strip() for part in rewards_field.split(",") if part.strip()]
    if not parts:
        return 0.0
    try:
        return float(parts[-1])
    except ValueError:
        return 0.0

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the comprehensive LedgerShield model comparison.")
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of models to test. Defaults to the full MODEL_TIERS list.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to write the JSON summary. Default: {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-model timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=PASS_THRESHOLD,
        help=f"Score threshold used for pass counts. Default: {PASS_THRESHOLD}",
    )
    return parser.parse_args()


def _selected_model_tiers(model_csv: str | None) -> list[tuple[str, str]]:
    if not model_csv:
        return MODEL_TIERS

    requested = [name.strip() for name in model_csv.split(",") if name.strip()]
    known_tiers = {model: tier for model, tier in MODEL_TIERS}
    selected: list[tuple[str, str]] = []
    for model in requested:
        tier = known_tiers.get(model, "Custom")
        selected.append((model, tier))
    return selected


def run_inference(
    model: str,
    api_key: str,
    *,
    timeout_seconds: int,
    pass_threshold: float,
) -> dict[str, Any]:
    """Run inference_llm_powered.py with specific model."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    env["API_BASE_URL"] = "https://api.openai.com/v1"
    env["MODEL_NAME"] = model
    env["ENV_URL"] = "http://127.0.0.1:8000"
    
    try:
        result = subprocess.run(
            [sys.executable, "inference_llm_powered.py"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            cwd=str(REPO_ROOT),
        )
        
        # Parse results from output
        scores = []
        api_calls = 0
        total_tokens = 0
        
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            end_match = END_RE.match(line)
            if end_match:
                scores.append(_score_from_end(end_match.group(3), end_match.group(4)))
                continue
            api_calls_match = API_CALLS_RE.match(line)
            if api_calls_match:
                api_calls = int(api_calls_match.group(1))
                continue
            elif 'Total tokens:' in line:
                try:
                    total_tokens = int(line.split(':')[1].strip().replace(',', ''))
                except:
                    pass

        if api_calls == 0:
            raise RuntimeError(
                "Run produced 0 API calls. The comparison likely fell back to heuristic logic instead of live inference."
            )
        if not scores:
            raise RuntimeError("Run did not produce parseable case scores.")
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "model": model,
            "average_score": round(avg_score, 4),
            "cases_passed": len([s for s in scores if s >= pass_threshold]),
            "total_cases": len(scores),
            "api_calls": api_calls,
            "total_tokens": total_tokens,
            "estimated_cost": round(total_tokens * 0.000005, 4),
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "model": model,
            "average_score": 0.0,
            "cases_passed": 0,
            "total_cases": 0,
            "api_calls": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
            "success": False,
            "error": str(e),
        }

def main():
    args = _parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    selected_model_tiers = _selected_model_tiers(args.models)
    print("="*100)
    print("COMPREHENSIVE OPENAI MODEL COMPARISON - LEDGERSHIELD")
    print("Testing models from weak (GPT-3.5) to SOTA (GPT-5.4)")
    print("="*100)
    print(f"\nTotal models to test: {len(selected_model_tiers)}")
    print("This will take approximately 10-15 minutes...\n")

    results = []

    for i, (model, tier) in enumerate(selected_model_tiers, 1):
        print(f"\n[{i}/{len(selected_model_tiers)}] Testing {model} ({tier})...")
        print("-" * 80)

        result = run_inference(
            model,
            api_key,
            timeout_seconds=args.timeout,
            pass_threshold=args.pass_threshold,
        )
        results.append({**result, "tier": tier})

        if result["success"]:
            print(f"  ✅ Score: {result['average_score']:.4f}")
            print(
                f"  📊 Cases: {result['cases_passed']}/{result['total_cases']} passed "
                f"(threshold {args.pass_threshold:.2f})"
            )
            print(f"  💰 Cost: ${result['estimated_cost']:.4f}")
            print(f"  🔢 API calls: {result['api_calls']}")
        else:
            print(f"  ❌ Failed: {result['error']}")

    # Sort by score
    results_sorted = sorted(results, key=lambda x: x["average_score"], reverse=True)

    # Print summary table
    print("\n" + "="*100)
    print("FINAL RESULTS - RANKED BY PERFORMANCE")
    print("="*100)
    print(f"{'Rank':<6} {'Model':<25} {'Tier':<18} {'Score':<10} {'Cases':<10} {'Cost':<12} {'API Calls':<10}")
    print("-"*100)

    for i, r in enumerate(results_sorted, 1):
        status = "✅" if r["success"] else "❌"
        cases = f"{r['cases_passed']}/{r['total_cases']}" if r["success"] else "N/A"
        print(f"{status} {i:<4} {r['model']:<25} {r['tier']:<18} "
              f"{r['average_score']:<10.4f} {cases:<10} ${r['estimated_cost']:<11.4f} {r['api_calls']:<10}")

    print("="*100)

    # Calculate separation
    successful = [r for r in results if r["success"] and r["total_cases"] > 0]
    scores: list[float] = []
    max_score = 0.0
    min_score = 0.0
    separation = 0.0
    if len(successful) >= 2:
        scores = [r["average_score"] for r in successful]
        max_score = max(scores)
        min_score = min(scores)
        separation = max_score - min_score

        print(f"\n📈 SCORE SEPARATION ANALYSIS:")
        print(f"   Best model: {max_score:.4f}")
        print(f"   Worst model: {min_score:.4f}")
        print(f"   Separation: {separation:.4f} ({separation/max_score*100:.1f}%)")

        if separation > 0.1:
            print(f"   ✅ STRONG separation - grader successfully distinguishes agents")
        elif separation > 0.05:
            print(f"   ⚠️  MODERATE separation")
        else:
            print(f"   ❌ WEAK separation - models too similar")

    # Save results
    output = {
        "experiment": "OpenAI Model Comparison (Weak to SOTA)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_threshold": args.pass_threshold,
        "results": results,
        "summary": {
            "total_models_tested": len(results),
            "successful_runs": len([r for r in results if r["success"]]),
            "score_range": f"{min(scores):.4f} - {max(scores):.4f}" if scores else "N/A",
            "separation": separation if successful else 0,
        }
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Detailed results saved to: {args.output}")
    print("="*100)

if __name__ == "__main__":
    main()
