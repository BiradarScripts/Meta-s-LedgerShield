#!/usr/bin/env python3
"""
Comprehensive OpenAI Model Comparison for LedgerShield
Tests models from weak (GPT-3.5) to SOTA (GPT-5.4)
"""

from __future__ import annotations

import json
import os
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

def run_inference(model: str, api_key: str) -> dict[str, Any]:
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
            timeout=600,
            env=env,
            cwd="/Users/aryamanpathak/meta-hackathon/Meta-s-LedgerShield"
        )
        
        # Parse results from output
        scores = []
        api_calls = 0
        total_tokens = 0
        
        for line in result.stdout.split('\n'):
            if '[END]' in line and 'rewards=' in line:
                # Extract final reward
                try:
                    rewards_part = line.split('rewards=')[1].split()[0]
                    final_reward = float(rewards_part.split(',')[-1])
                    scores.append(final_reward)
                except:
                    pass
            elif 'Total API calls:' in line:
                try:
                    api_calls = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'Total tokens:' in line:
                try:
                    total_tokens = int(line.split(':')[1].strip().replace(',', ''))
                except:
                    pass
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "model": model,
            "average_score": round(avg_score, 4),
            "cases_passed": len([s for s in scores if s >= 0.6]),
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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    print("="*100)
    print("COMPREHENSIVE OPENAI MODEL COMPARISON - LEDGERSHIELD")
    print("Testing models from weak (GPT-3.5) to SOTA (GPT-5.4)")
    print("="*100)
    print(f"\nTotal models to test: {len(MODEL_TIERS)}")
    print("This will take approximately 10-15 minutes...\n")
    
    results = []
    
    for i, (model, tier) in enumerate(MODEL_TIERS, 1):
        print(f"\n[{i}/{len(MODEL_TIERS)}] Testing {model} ({tier})...")
        print("-" * 80)
        
        result = run_inference(model, api_key)
        results.append({**result, "tier": tier})
        
        if result["success"]:
            print(f"  ✅ Score: {result['average_score']:.4f}")
            print(f"  📊 Cases: {result['cases_passed']}/{result['total_cases']} passed")
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
        "date": "2025-01-06",
        "results": results,
        "summary": {
            "total_models_tested": len(results),
            "successful_runs": len([r for r in results if r["success"]]),
            "score_range": f"{min(scores):.4f} - {max(scores):.4f}" if scores else "N/A",
            "separation": separation if successful else 0,
        }
    }
    
    with open("comprehensive_model_comparison.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: comprehensive_model_comparison.json")
    print("="*100)

if __name__ == "__main__":
    main()
