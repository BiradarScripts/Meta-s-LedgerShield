from __future__ import annotations

"""
Baseline Scoring Script - LedgerShield
======================================
Pre-submission scoring simulation to test grader behavior.

This script simulates different agent strategies to:
1. Estimate baseline scores before submission
2. Inspect grader separation between weak and strong agents
3. Identify tasks where the grader is too harsh or too permissive

Usage:
    python test_scoring.py
"""

from dataclasses import dataclass
from typing import Any

from server.environment import LedgerShieldEnvironment
from server.grading import score_submission
from server.outcome_simulator import simulate_outcome


@dataclass
class AgentStrategy:
    name: str
    description: str
    budget: float
    confidence: float


class BaselineScorer:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    def _task_a_fields(self, gold: dict[str, Any]) -> dict[str, Any]:
        return dict(gold.get("fields", gold.get("extracted_fields", {})))

    def _trajectory_for_strategy(
        self,
        strategy: AgentStrategy,
        task_type: str,
        gold: dict[str, Any],
    ) -> list[dict[str, Any]]:
        trajectories: dict[str, list[dict[str, Any]]] = {
            "random": [],
            "no-research": [],
            "partial-ocr": [
                {"action_type": "ocr", "payload": {"mode": "fast"}, "success": True},
            ],
            "partial-research": {
                "task_a": [
                    {"action_type": "ocr", "payload": {"mode": "fast"}, "success": True},
                    {"action_type": "zoom", "payload": {}, "success": True},
                ],
                "task_b": [
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "lookup_po", "payload": {}, "success": True},
                ],
                "task_c": [
                    {"action_type": "search_ledger", "payload": {}, "success": True},
                ],
                "task_d": [
                    {"action_type": "inspect_email_thread", "payload": {}, "success": True},
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                ],
            },
            "good-effort": {
                "task_a": [
                    {"action_type": "ocr", "payload": {"mode": "accurate"}, "success": True},
                    {"action_type": "zoom", "payload": {}, "success": True},
                ],
                "task_b": [
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "lookup_po", "payload": {}, "success": True},
                    {"action_type": "lookup_receipt", "payload": {}, "success": True},
                ],
                "task_c": [
                    {"action_type": "search_ledger", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                ],
                "task_d": [
                    {"action_type": "inspect_email_thread", "payload": {}, "success": True},
                    {"action_type": "lookup_vendor_history", "payload": {}, "success": True},
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                ],
            },
            "near-perfect": {
                "task_a": [
                    {"action_type": "ocr", "payload": {"mode": "accurate"}, "success": True},
                    {"action_type": "zoom", "payload": {}, "success": True},
                ],
                "task_b": [
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "lookup_po", "payload": {}, "success": True},
                    {"action_type": "lookup_receipt", "payload": {}, "success": True},
                ],
                "task_c": [
                    {"action_type": "search_ledger", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                ],
                "task_d": [
                    {"action_type": "inspect_email_thread", "payload": {}, "success": True},
                    {"action_type": "lookup_vendor_history", "payload": {}, "success": True},
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                ],
            },
            "gold-standard": {
                "task_a": [
                    {"action_type": "ocr", "payload": {"mode": "accurate"}, "success": True},
                    {"action_type": "zoom", "payload": {}, "success": True},
                ],
                "task_b": [
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "lookup_po", "payload": {}, "success": True},
                    {"action_type": "lookup_receipt", "payload": {}, "success": True},
                ],
                "task_c": [
                    {"action_type": "search_ledger", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                    {"action_type": "flag_duplicate_cluster_review", "payload": {}, "success": True},
                ],
                "task_d": [
                    {"action_type": "inspect_email_thread", "payload": {}, "success": True},
                    {"action_type": "lookup_vendor_history", "payload": {}, "success": True},
                    {"action_type": "lookup_policy", "payload": {}, "success": True},
                    {"action_type": "compare_bank_account", "payload": {}, "success": True},
                    {"action_type": "request_callback_verification", "payload": {}, "success": True},
                ],
            },
        }

        base = trajectories.get(strategy.name, [])
        if isinstance(base, dict):
            trajectory = list(base.get(task_type, []))
        else:
            trajectory = list(base)

        if gold.get("unsafe_if_pay") and strategy.name in {"near-perfect", "gold-standard"}:
            if not any(step["action_type"] == "request_callback_verification" for step in trajectory):
                trajectory.append(
                    {"action_type": "request_callback_verification", "payload": {}, "success": True}
                )

        return trajectory

    def _submission_for_strategy(
        self,
        strategy: AgentStrategy,
        task_type: str,
        gold: dict[str, Any],
    ) -> dict[str, Any]:
        task_a_fields = self._task_a_fields(gold)
        decision_default = gold.get("decision", "NEEDS_REVIEW")

        if strategy.name in {"random", "no-research", "partial-ocr"}:
            return {
                "decision": "NEEDS_REVIEW",
                "confidence": strategy.confidence,
            }

        if strategy.name == "partial-research":
            if task_type == "task_a":
                return {
                    "decision": "NEEDS_REVIEW",
                    "confidence": strategy.confidence,
                    "extracted_fields": {
                        "vendor_name": task_a_fields.get("vendor_name", ""),
                        "invoice_number": task_a_fields.get("invoice_number", ""),
                    },
                    "line_items": [],
                    "evidence_map": {},
                }
            return {
                "decision": "NEEDS_REVIEW",
                "confidence": strategy.confidence,
            }

        if strategy.name == "good-effort":
            if task_type == "task_a":
                fields = dict(task_a_fields)
                fields.pop("bank_account", None)
                return {
                    "decision": "NEEDS_REVIEW",
                    "confidence": strategy.confidence,
                    "extracted_fields": fields,
                    "line_items": list(gold.get("line_items", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            if task_type == "task_b":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "discrepancies": list(gold.get("discrepancies", []))[:1],
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": {},
                }
            if task_type == "task_c":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": list(gold.get("fraud_flags", []))[:1],
                    "evidence_map": {},
                }
            return {
                "decision": decision_default,
                "confidence": strategy.confidence,
                "reason_codes": list(gold.get("reason_codes", [])),
                "policy_checks": dict(gold.get("policy_checks", {})),
                "evidence_map": {},
                "counterfactual": "Short",
            }

        if strategy.name == "near-perfect":
            if task_type == "task_a":
                return {
                    "decision": "NEEDS_REVIEW",
                    "confidence": strategy.confidence,
                    "extracted_fields": dict(task_a_fields),
                    "line_items": list(gold.get("line_items", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            if task_type == "task_b":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "discrepancies": list(gold.get("discrepancies", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            if task_type == "task_c":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": list(gold.get("fraud_flags", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            return {
                "decision": decision_default,
                "confidence": strategy.confidence,
                "reason_codes": list(gold.get("reason_codes", [])),
                "policy_checks": dict(gold.get("policy_checks", {})),
                "evidence_map": dict(gold.get("evidence_targets", {})),
                "counterfactual": "Would PAY if conditions were met with proper verification.",
            }

        if strategy.name == "gold-standard":
            if task_type == "task_a":
                return {
                    "decision": "NEEDS_REVIEW",
                    "confidence": strategy.confidence,
                    "extracted_fields": dict(task_a_fields),
                    "line_items": list(gold.get("line_items", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            if task_type == "task_b":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "discrepancies": list(gold.get("discrepancies", [])),
                    "policy_checks": dict(gold.get("policy_checks", {})),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            if task_type == "task_c":
                return {
                    "decision": decision_default,
                    "confidence": strategy.confidence,
                    "duplicate_links": list(gold.get("duplicate_links", [])),
                    "fraud_flags": list(gold.get("fraud_flags", [])),
                    "evidence_map": dict(gold.get("evidence_targets", {})),
                }
            return {
                "decision": decision_default,
                "confidence": strategy.confidence,
                "reason_codes": list(gold.get("reason_codes", [])),
                "policy_checks": dict(gold.get("policy_checks", {})),
                "evidence_map": dict(gold.get("evidence_targets", {})),
                "counterfactual": gold.get(
                    "counterfactual",
                    "Would PAY if conditions were met after callback verification and policy compliance.",
                ),
            }

        return {
            "decision": "NEEDS_REVIEW",
            "confidence": strategy.confidence,
        }

    def simulate_agent(self, env: LedgerShieldEnvironment, strategy: AgentStrategy) -> dict[str, Any]:
        env.reset(case_id=env.current_case["case_id"])
        task_type = env.current_case["task_type"]
        gold = env.current_case["gold"]

        budget_penalty = 0.0
        if strategy.budget > 0:
            budget_used = env._state.budget_total * strategy.budget
            budget_penalty = (budget_used / max(env._state.budget_total, 1.0)) * 0.12

        trajectory = self._trajectory_for_strategy(strategy, task_type, gold)
        submission = self._submission_for_strategy(strategy, task_type, gold)
        outcome = simulate_outcome(
            submitted=submission,
            trajectory=trajectory,
            hidden_world=env._hidden_world,
        )

        score, breakdown = score_submission(
            task_type=task_type,
            submitted=submission,
            gold=gold,
            budget_penalty=budget_penalty,
            trajectory=trajectory,
            outcome=outcome,
            investigation_summary={
                "tool_calls": len(trajectory),
                "interventions_taken": sum(
                    1 for step in trajectory if step.get("action_type", "").startswith("request_")
                ),
                "revealed_artifact_ids": [],
                "observed_risk_signals": [],
            },
        )

        return {
            "strategy": strategy.name,
            "task_type": task_type,
            "case_id": env.current_case["case_id"],
            "score": score,
            "breakdown": breakdown,
            "budget_penalty": budget_penalty,
            "outcome_type": outcome.get("outcome_type", "unknown"),
        }

    def run_all_strategies(self) -> list[dict[str, Any]]:
        strategies = [
            AgentStrategy("random", "Random decision baseline", 0.0, 0.20),
            AgentStrategy("no-research", "Sees docs but does no meaningful investigation", 0.05, 0.35),
            AgentStrategy("partial-ocr", "Does OCR only", 0.15, 0.45),
            AgentStrategy("partial-research", "Does a little investigation", 0.30, 0.55),
            AgentStrategy("good-effort", "Reasonable agent with some misses", 0.55, 0.70),
            AgentStrategy("near-perfect", "Almost perfect agent", 0.75, 0.85),
            AgentStrategy("gold-standard", "Reference-quality agent", 1.00, 0.95),
        ]

        env_template = LedgerShieldEnvironment()
        test_cases = [str(case["case_id"]) for case in env_template.db.get("cases", []) if case.get("case_id")]

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

                score = result["score"]
                if score >= 0.90:
                    indicator = "🟢"
                elif score >= 0.50:
                    indicator = "🟡"
                elif score >= 0.10:
                    indicator = "🟠"
                else:
                    indicator = "🔴"

                print(
                    f"   {indicator} {strategy.name:20s}: "
                    f"{score:.4f} "
                    f"(penalty: {result['budget_penalty']:.4f}, outcome: {result['outcome_type']})"
                )

        return self.results

    def summary(self) -> None:
        print("\n" + "=" * 70)
        print("SUMMARY BY STRATEGY")
        print("=" * 70)

        by_strategy: dict[str, list[float]] = {}
        for result in self.results:
            by_strategy.setdefault(result["strategy"], []).append(result["score"])

        print(f"\n{'Strategy':<20} {'Avg Score':>10} {'Min':>8} {'Max':>8}")
        print("-" * 50)

        sorted_strategies = sorted(
            by_strategy.items(),
            key=lambda item: sum(item[1]) / len(item[1]),
            reverse=True,
        )

        for strategy, scores in sorted_strategies:
            avg_score = sum(scores) / len(scores)
            print(f"{strategy:<20} {avg_score:>10.4f} {min(scores):>8.4f} {max(scores):>8.4f}")

        print("\n" + "=" * 70)
        print("SUMMARY BY TASK")
        print("=" * 70)

        by_task: dict[str, list[float]] = {}
        for result in self.results:
            by_task.setdefault(result["task_type"], []).append(result["score"])

        print(f"\n{'Task':<10} {'Avg Score':>10} {'Cases':>8}")
        print("-" * 35)

        for task, scores in sorted(by_task.items()):
            avg_score = sum(scores) / len(scores)
            print(f"{task:<10} {avg_score:>10.4f} {len(scores):>8}")

        print("\n" + "=" * 70)
        print("GRADER SENSITIVITY ANALYSIS")
        print("=" * 70)

        gold_scores = [result["score"] for result in self.results if result["strategy"] == "gold-standard"]
        random_scores = [result["score"] for result in self.results if result["strategy"] == "random"]

        avg_gold = sum(gold_scores) / len(gold_scores)
        avg_random = sum(random_scores) / len(random_scores)
        spread = avg_gold - avg_random

        print(f"\nGold Standard Avg: {avg_gold:.4f}")
        print(f"Random Baseline Avg: {avg_random:.4f}")
        print(f"Score Spread: {spread:.4f}")

        if spread > 0.70:
            print("\n✅ Grader is STRICT - good at distinguishing quality")
        elif spread > 0.30:
            print("\n⚠️ Grader is MODERATE - some separation, but could be stronger")
        else:
            print("\n❌ Grader is PERMISSIVE - it may not distinguish quality well")

    def print_recommendations(self) -> None:
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)
        print(
            """
Based on the scoring:

1. If gold-standard scores are far below 1.0, the grader or fixtures may be inconsistent.
2. If random baseline scores are too high, the grader may be too permissive.
3. If the spread between weak and strong agents is small, the grader may not separate quality well.
4. If specific tasks are consistently weak, those tasks may need reward or fixture tuning.
"""
        )


def main() -> None:
    scorer = BaselineScorer()
    scorer.run_all_strategies()
    scorer.summary()
    scorer.print_recommendations()


if __name__ == "__main__":
    main()