"""
Baseline Scoring Script - LedgerShield
======================================
Pre-submission scoring simulation to test grader performance.

This script simulates different LLM agent strategies to:
1. Get baseline scores before submission
2. Identify grader behavior (strict vs permissive)
3. Find areas for improvement

Usage:
    python test_scoring.py
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass

from envs.ledgershield_env.server.environment import LedgerShieldEnvironment
from envs.ledgershield_env.server.grading import score_submission
from envs.ledgershield_env import LedgerShieldAction


@dataclass
class AgentStrategy:
    name: str
    description: str
    budget: float  # How much budget to use (0.0 = no research, 1.0 = full research)


class BaselineScorer:
    """Tests different agent strategies to score environment difficulty."""
    
    def __init__(self):
        self.results = []
    
    def simulate_agent(self, env: LedgerShieldEnvironment, strategy: AgentStrategy) -> Dict:
        """Simulate an agent following a strategy."""
        env.reset(case_id=env.current_case["case_id"])
        task_type = env.current_case["task_type"]
        gold = env.current_case["gold"]
        
        # Calculate budget usage
        budget_penalty = 0.0
        if strategy.budget > 0:
            budget_used = env._state.budget_total * strategy.budget
            budget_penalty = (budget_used / env._state.budget_total) * 0.15
        
        # Different strategies based on what agent knows
        if strategy.name == "random":
            # Agent knows nothing, submits random decision
            submission = {"decision": "NEEDS_REVIEW"}
        
        elif strategy.name == "no-research":
            # Agent only sees docs, submits based on minimal info
            submission = {"decision": "NEEDS_REVIEW"}
        
        elif strategy.name == "partial-ocr":
            # Agent does OCR but no other lookups
            submission = {"decision": "NEEDS_REVIEW"}
        
        elif strategy.name == "partial-research":
            # Agent does some lookups but incomplete
            if task_type == "task_a":
                submission = {
                    "decision": "NEEDS_REVIEW",
                    "extracted_fields": {
                        "vendor_name": gold["extracted_fields"].get("vendor_name", ""),
                        "invoice_number": gold["extracted_fields"].get("invoice_number", ""),
                    },
                    "line_items": [],
                    "evidence_map": {}
                }
            else:
                submission = {"decision": "NEEDS_REVIEW"}
        
        elif strategy.name == "good-effort":
            # Agent tries hard but misses some details
            if task_type == "task_a":
                fields = dict(gold["extracted_fields"])
                fields.pop("bank_account", None)  # Missing one field
                submission = {
                    "decision": "NEEDS_REVIEW",
                    "extracted_fields": fields,
                    "line_items": list(gold["line_items"]),
                    "evidence_map": dict(gold["evidence_targets"])
                }
            elif task_type == "task_b":
                submission = {
                    "decision": gold.get("decision", "HOLD"),
                    "discrepancies": gold.get("discrepancies", [])[:1],  # Missing some
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": {}
                }
            elif task_type == "task_c":
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": gold.get("fraud_flags", [])[:1],  # Missing some
                    "evidence_map": {}
                }
            else:  # task_d
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "reason_codes": list(gold.get("reason_codes", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": {},
                    "counterfactual": "Short"  # Too short
                }
        
        elif strategy.name == "near-perfect":
            # Agent gets almost everything right
            if task_type == "task_a":
                submission = {
                    "decision": "NEEDS_REVIEW",
                    "extracted_fields": dict(gold["extracted_fields"]),
                    "line_items": list(gold["line_items"]),
                    "evidence_map": dict(gold["evidence_targets"])
                }
            elif task_type == "task_b":
                submission = {
                    "decision": gold.get("decision", "HOLD"),
                    "discrepancies": list(gold.get("discrepancies", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold["evidence_targets"])
                }
            elif task_type == "task_c":
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": list(gold.get("fraud_flags", [])),
                    "evidence_map": dict(gold["evidence_targets"])
                }
            else:
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "reason_codes": list(gold.get("reason_codes", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                    "counterfactual": "Would PAY if conditions were met with proper verification."
                }
        
        elif strategy.name == "gold-standard":
            # Perfect submission
            if task_type == "task_a":
                submission = {
                    "decision": "NEEDS_REVIEW",
                    "extracted_fields": dict(gold.get("extracted_fields", gold.get("fields", {}))),
                    "line_items": list(gold.get("line_items", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {}))
                }
            elif task_type == "task_b":
                submission = {
                    "decision": gold.get("decision", "HOLD"),
                    "discrepancies": list(gold.get("discrepancies", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold.get("evidence_targets", {}))
                }
            elif task_type == "task_c":
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": list(gold.get("fraud_flags", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {}))
                }
            else:
                submission = {
                    "decision": gold.get("decision", "ESCALATE_FRAUD"),
                    "reason_codes": list(gold.get("reason_codes", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                    "counterfactual": gold.get("counterfactual", "Would PAY if conditions were met.")
                }
        else:
            submission = {"decision": "NEEDS_REVIEW"}
        
        # Score the submission
        score, breakdown = score_submission(task_type, submission, gold, budget_penalty)
        
        return {
            "strategy": strategy.name,
            "task_type": task_type,
            "case_id": env.current_case["case_id"],
            "score": score,
            "breakdown": breakdown,
            "budget_penalty": budget_penalty
        }
    
    def run_all_strategies(self):
        """Run all strategies on all test cases."""
        strategies = [
            AgentStrategy("random", "Random decision (baseline)", 0.0),
            AgentStrategy("no-research", "Sees docs but no research", 0.1),
            AgentStrategy("partial-ocr", "Does OCR only", 0.2),
            AgentStrategy("partial-research", "Does some lookups", 0.4),
            AgentStrategy("good-effort", "Tries hard but misses some", 0.6),
            AgentStrategy("near-perfect", "Almost perfect", 0.8),
            AgentStrategy("gold-standard", "Perfect submission", 1.0),
        ]
        
        test_cases = [
            "CASE-A-001", "CASE-A-002",
            "CASE-B-001", "CASE-C-001", "CASE-D-001"
        ]
        
        print("=" * 70)
        print("LEDGERSHIELD BASELINE SCORING")
        print("=" * 70)
        
        for case_id in test_cases:
            print(f"\n📋 Testing: {case_id}")
            env = LedgerShieldEnvironment()
            env.reset(case_id=case_id)
            
            print(f"   Task: {env.current_case['task_type']}")
            print(f"   Difficulty: {env.current_case.get('difficulty', 'unknown')}")
            
            for strategy in strategies:
                result = self.simulate_agent(env, strategy)
                self.results.append(result)
                
                # Color code scores
                score = result["score"]
                if score >= 0.9:
                    indicator = "🟢"
                elif score >= 0.5:
                    indicator = "🟡"
                elif score >= 0.1:
                    indicator = "🟠"
                else:
                    indicator = "🔴"
                
                print(f"   {indicator} {strategy.name:20s}: {score:.4f} (penalty: {result['budget_penalty']:.4f})")
        
        return self.results
    
    def summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 70)
        print("SUMMARY BY STRATEGY")
        print("=" * 70)
        
        by_strategy = {}
        for r in self.results:
            strategy = r["strategy"]
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(r["score"])
        
        print(f"\n{'Strategy':<20} {'Avg Score':>10} {'Min':>8} {'Max':>8}")
        print("-" * 50)
        
        sorted_strategies = sorted(by_strategy.items(), 
                                   key=lambda x: sum(x[1])/len(x[1]), 
                                   reverse=True)
        
        for strategy, scores in sorted_strategies:
            avg = sum(scores) / len(scores)
            min_s = min(scores)
            max_s = max(scores)
            print(f"{strategy:<20} {avg:>10.4f} {min_s:>8.4f} {max_s:>8.4f}")
        
        print("\n" + "=" * 70)
        print("SUMMARY BY TASK")
        print("=" * 70)
        
        by_task = {}
        for r in self.results:
            task = r["task_type"]
            if task not in by_task:
                by_task[task] = []
            by_task[task].append(r["score"])
        
        print(f"\n{'Task':<10} {'Avg Score':>10} {'Cases':>8}")
        print("-" * 35)
        
        for task, scores in sorted(by_task.items()):
            avg = sum(scores) / len(scores)
            print(f"{task:<10} {avg:>10.4f} {len(scores):>8}")
        
        # Calculate grader sensitivity
        print("\n" + "=" * 70)
        print("GRADER SENSITIVITY ANALYSIS")
        print("=" * 70)
        
        gold_scores = [r["score"] for r in self.results if r["strategy"] == "gold-standard"]
        random_scores = [r["score"] for r in self.results if r["strategy"] == "random"]
        
        avg_gold = sum(gold_scores) / len(gold_scores)
        avg_random = sum(random_scores) / len(random_scores)
        spread = avg_gold - avg_random
        
        print(f"\nGold Standard Avg: {avg_gold:.4f}")
        print(f"Random Baseline Avg: {avg_random:.4f}")
        print(f"Score Spread: {spread:.4f}")
        
        if spread > 0.7:
            print("\n✅ Grader is STRICT - good at distinguishing quality")
        elif spread > 0.3:
            print("\n⚠️ Grader is MODERATE - some区分度")
        else:
            print("\n❌ Grader is PERMISSIVE - may not区分度 quality well")


def main():
    scorer = BaselineScorer()
    scorer.run_all_strategies()
    scorer.summary()
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("""
Based on the scoring:

1. If gold-standard scores < 1.0 → Grader has bugs
2. If random baseline scores > 0.3 → Grader is too permissive  
3. If spread is small → Grader can't distinguish agent quality
4. If specific tasks have low scores → Those tasks need grader tuning

Run this before submission to ensure grader works correctly!
""")


if __name__ == "__main__":
    main()
