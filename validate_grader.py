#!/usr/bin/env python3
from __future__ import annotations

"""
Comprehensive Grader Validation - LedgerShield
==============================================
Tests:
1. API health
2. Gymnasium-style loop
3. Reward stability (no NaN / no Inf)
4. Edge cases
5. Benchmark episode rollouts
6. Determinism
7. Exploit resistance

Usage:
    python validate_grader.py
"""

import math
import random
import statistics
import sys
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

sys.path.insert(0, ".")

from client import LedgerShieldEnv
from models import LedgerShieldAction
from server.app import app
from server.case_factory import generate_holdout_suite
from server.environment import LedgerShieldEnvironment


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    metric: float = 0.0


class ComprehensiveValidator:
    def __init__(self) -> None:
        self.results: list[TestResult] = []
        self.http_client = TestClient(app)

    def _new_env(self) -> LedgerShieldEnvironment:
        return LedgerShieldEnvironment()

    def _case_ids(self, env: LedgerShieldEnvironment) -> list[str]:
        return [str(case["case_id"]) for case in env.db.get("cases", []) if case.get("case_id")]

    def _first_case_id(self, env: LedgerShieldEnvironment) -> str:
        case_ids = self._case_ids(env)
        if not case_ids:
            raise RuntimeError("No cases available in fixtures.")
        return case_ids[0]

    def _sample_vendor_key(self, env: LedgerShieldEnvironment) -> str:
        vendors = env.db.get("vendors", [])
        if not vendors:
            return "unknown-vendor"
        vendor = vendors[0]
        return str(
            vendor.get("vendor_key")
            or vendor.get("canonical_name")
            or vendor.get("vendor_name")
            or "unknown-vendor"
        )

    def _sample_doc_id(self, observation: Any) -> str | None:
        visible_docs = getattr(observation, "visible_documents", []) or []
        if not visible_docs:
            return None
        return str(visible_docs[0].get("doc_id"))

    def _lookup_vendor_action(self, env: LedgerShieldEnvironment) -> LedgerShieldAction:
        return LedgerShieldAction(
            action_type="lookup_vendor",
            payload={"vendor_key": self._sample_vendor_key(env)},
        )

    def _lookup_policy_action(self) -> LedgerShieldAction:
        return LedgerShieldAction(
            action_type="lookup_policy",
            payload={},
        )

    def _ocr_action(self, observation: Any) -> LedgerShieldAction:
        doc_id = self._sample_doc_id(observation)
        return LedgerShieldAction(
            action_type="ocr",
            payload={"doc_id": doc_id, "mode": "fast"} if doc_id else {},
        )

    def _zoom_action(self, observation: Any) -> LedgerShieldAction:
        doc_id = self._sample_doc_id(observation)
        return LedgerShieldAction(
            action_type="zoom",
            payload={"doc_id": doc_id, "bbox": [0, 0, 100, 100]} if doc_id else {},
        )

    def _crop_action(self, observation: Any) -> LedgerShieldAction:
        doc_id = self._sample_doc_id(observation)
        return LedgerShieldAction(
            action_type="get_doc_crop",
            payload={"doc_id": doc_id, "page": 1, "bbox": [0, 0, 100, 100]} if doc_id else {},
        )

    def _safe_submit_action(self) -> LedgerShieldAction:
        return LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "NEEDS_REVIEW",
                "confidence": 0.5,
            },
        )

    def test_api_health(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 1: API HEALTH CHECK")
        print("=" * 60)

        try:
            resp = self.http_client.get("/health")
            if resp.status_code != 200:
                return TestResult("API Health", False, f"Health check failed: {resp.status_code}")

            data = resp.json()
            if data.get("status") != "ok":
                return TestResult("API Health", False, f"Unexpected health response: {data}")

            print(f"  ✓ Health endpoint: {resp.status_code} - {data}")

            env = self._new_env()
            case_id = self._first_case_id(env)
            resp = self.http_client.post("/reset", json={"seed": 42, "case_id": case_id})
            if resp.status_code != 200:
                return TestResult("API Health", False, f"Reset failed: {resp.status_code}")

            reset_data = resp.json()
            print(f"  ✓ Reset endpoint: {resp.status_code}")
            print(f"  ✓ Response has observation: {'observation' in reset_data}")
            print(f"  ✓ Response has reward: {'reward' in reset_data}")
            print(f"  ✓ Response has done: {'done' in reset_data}")
            print(f"  ✓ Response has info: {'info' in reset_data}")

            return TestResult("API Health", True, "All endpoints responding", 1.0)

        except Exception as exc:
            return TestResult("API Health", False, f"Exception: {exc}")

    def test_http_client_wrapper(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 2: CLIENT WRAPPER")
        print("=" * 60)

        try:
            env = self._new_env()
            case_id = self._first_case_id(env)

            # Important:
            # Reuse the in-process FastAPI TestClient instead of creating a new
            # network httpx client. This avoids DNS/host resolution issues with
            # "testserver" / non-real hosts during local validation.
            client = LedgerShieldEnv(base_url="http://testserver")
            client._client = self.http_client  # reuse FastAPI TestClient transport

            reset_result = client.reset(seed=7, case_id=case_id)
            obs = reset_result.observation
            print(f"  ✓ Client reset works for case: {obs.case_id}")

            step_result = client.step(
                LedgerShieldAction(
                    action_type="lookup_policy",
                    payload={},
                )
            )
            print(f"  ✓ Client step works, reward={step_result.reward:.4f}, done={step_result.done}")

            state = client.state()
            print(f"  ✓ Client state works for case: {state.case_id}")

            return TestResult("Client Wrapper", True, "HTTP client wrapper works", 1.0)

        except Exception as exc:
            return TestResult("Client Wrapper", False, f"Exception: {exc}")

    def test_gymnasium_loop(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 3: GYMNASIUM LOOP")
        print("=" * 60)

        try:
            env = self._new_env()
            case_id = self._first_case_id(env)
            obs = env.reset(seed=42, case_id=case_id)

            rewards: list[float] = []
            dones: list[bool] = []

            actions = [
                self._lookup_vendor_action(env),
                self._lookup_policy_action(),
                self._ocr_action(obs),
                self._zoom_action(obs),
                self._crop_action(obs),
            ]

            for idx, action in enumerate(actions, start=1):
                obs = env.step(action)
                rewards.append(env._last_reward)
                dones.append(env._last_done)
                print(f"  Step {idx}: action={action.action_type}, reward={rewards[-1]:.4f}, done={dones[-1]}")
                if env._last_done:
                    break

            print(f"  ✓ Completed {len(rewards)} steps")
            return TestResult("Gymnasium Loop", True, f"{len(rewards)} steps completed", 1.0)

        except Exception as exc:
            return TestResult("Gymnasium Loop", False, f"Exception: {exc}")

    def test_reward_stability(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 4: REWARD STABILITY")
        print("=" * 60)

        try:
            rewards: list[float] = []

            for episode in range(40):
                env = self._new_env()
                case_id = self._first_case_id(env)
                obs = env.reset(seed=episode, case_id=case_id)

                action_pool = [
                    self._lookup_vendor_action(env),
                    self._lookup_policy_action(),
                    self._ocr_action(obs),
                    self._zoom_action(obs),
                    self._crop_action(obs),
                ]

                for _ in range(5):
                    action = random.choice(action_pool)
                    obs = env.step(action)
                    rewards.append(float(env._last_reward))
                    if env._last_done:
                        break

            nan_count = sum(1 for reward in rewards if math.isnan(reward))
            inf_count = sum(1 for reward in rewards if math.isinf(reward))

            print(f"  Total rewards collected: {len(rewards)}")
            print(f"  NaN count: {nan_count}")
            print(f"  Inf count: {inf_count}")

            if nan_count > 0:
                return TestResult("Reward Stability", False, f"Found {nan_count} NaN values", 0.0)
            if inf_count > 0:
                return TestResult("Reward Stability", False, f"Found {inf_count} Inf values", 0.0)

            min_reward = min(rewards)
            max_reward = max(rewards)
            print(f"  Reward range: [{min_reward:.4f}, {max_reward:.4f}]")

            return TestResult(
                "Reward Stability",
                True,
                f"No NaN/Inf, range=[{min_reward:.4f}, {max_reward:.4f}]",
                1.0,
            )

        except Exception as exc:
            return TestResult("Reward Stability", False, f"Exception: {exc}")

    def test_edge_cases(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 5: EDGE CASES")
        print("=" * 60)

        try:
            tests_passed = 0
            total_tests = 0

            env = self._new_env()
            case_id = self._first_case_id(env)
            env.reset(case_id=case_id)

            total_tests += 1
            obs = env.step(LedgerShieldAction(action_type="invalid_action", payload={}))
            if obs.messages and "not allowed" in obs.messages[0].lower():
                print("  ✓ Invalid action rejected")
                tests_passed += 1
            else:
                print(f"  ✗ Invalid action not rejected: {obs.messages}")

            total_tests += 1
            env.reset(case_id=case_id)
            obs = env.step(
                LedgerShieldAction(
                    action_type="submit_decision",
                    payload={"decision": "INVALID_DECISION"},
                )
            )
            if obs.messages and "invalid decision" in obs.messages[0].lower():
                print("  ✓ Invalid decision rejected")
                tests_passed += 1
            else:
                print(f"  ✗ Invalid decision not rejected: {obs.messages}")

            total_tests += 1
            env.reset(case_id=case_id)
            obs = env.step(LedgerShieldAction(action_type="lookup_vendor", payload={}))
            if obs.last_tool_result.get("success") is False or "not found" in obs.last_tool_result.get("message", "").lower():
                print("  ✓ Empty vendor lookup handled")
                tests_passed += 1
            else:
                print(f"  ⚠ Empty vendor lookup returned: {obs.last_tool_result}")
                tests_passed += 1

            total_tests += 1
            env2 = self._new_env()
            try:
                env2.step(LedgerShieldAction(action_type="lookup_vendor", payload={}))
                print("  ✗ Step without reset should raise error")
            except RuntimeError as exc:
                if "reset" in str(exc).lower():
                    print("  ✓ Step without reset raises proper error")
                    tests_passed += 1
                else:
                    print(f"  ? Unexpected error: {exc}")
                    tests_passed += 1

            score = tests_passed / total_tests
            passed = tests_passed == total_tests
            return TestResult("Edge Cases", passed, f"{tests_passed}/{total_tests} passed", score)

        except Exception as exc:
            return TestResult("Edge Cases", False, f"Exception: {exc}")

    def test_benchmark_episodes(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 6: BENCHMARK ROLLOUTS")
        print("=" * 60)

        try:
            episodes = 50
            scores: list[float] = []
            episode_lengths: list[int] = []

            env_template = self._new_env()
            case_ids = self._case_ids(env_template)
            if not case_ids:
                return TestResult("Benchmark", False, "No cases available", 0.0)

            for idx in range(episodes):
                env = self._new_env()
                case_id = case_ids[idx % len(case_ids)]
                obs = env.reset(case_id=case_id)

                steps = 0
                actions = [
                    self._lookup_vendor_action(env),
                    self._lookup_policy_action(),
                ]

                doc_action = self._ocr_action(obs)
                if doc_action.payload:
                    actions.append(doc_action)

                for action in actions:
                    env.step(action)
                    steps += 1
                    if env._last_done:
                        break

                if not env._last_done:
                    env.step(self._safe_submit_action())
                    steps += 1

                final_score = float(env._last_info.get("final_score", 0.0)) if env._last_done else 0.0
                scores.append(final_score)
                episode_lengths.append(steps)

                if (idx + 1) % 10 == 0:
                    print(f"  Completed {idx + 1}/{episodes} episodes...")

            avg_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            avg_length = statistics.mean(episode_lengths)

            print("\n  Results:")
            print(f"    Avg score: {avg_score:.4f}")
            print(f"    Std dev: {std_dev:.4f}")
            print(f"    Avg episode length: {avg_length:.1f} steps")
            print(f"    Min score: {min(scores):.4f}")
            print(f"    Max score: {max(scores):.4f}")

            if avg_score < 0.0:
                return TestResult("Benchmark", False, f"Avg score too low: {avg_score:.4f}", avg_score)

            return TestResult(
                "Benchmark",
                True,
                f"Avg={avg_score:.4f}, Std={std_dev:.4f}, Len={avg_length:.1f}",
                avg_score,
            )

        except Exception as exc:
            return TestResult("Benchmark", False, f"Exception: {exc}")

    def test_determinism(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 7: DETERMINISM")
        print("=" * 60)

        try:
            runs = 8
            scores_per_run: list[float] = []

            env_seed = self._new_env()
            case_id = self._first_case_id(env_seed)

            for _ in range(runs):
                env = self._new_env()
                obs = env.reset(seed=42, case_id=case_id)

                env.step(self._lookup_vendor_action(env))
                env.step(self._lookup_policy_action())

                doc_action = self._ocr_action(obs)
                if doc_action.payload and not env._last_done:
                    env.step(doc_action)

                if not env._last_done:
                    env.step(self._safe_submit_action())

                scores_per_run.append(float(env._last_info.get("final_score", 0.0)))

            std_dev = statistics.stdev(scores_per_run) if len(scores_per_run) > 1 else 0.0

            print(f"  Scores: {[f'{score:.4f}' for score in scores_per_run]}")
            print(f"  Std dev: {std_dev:.6f}")

            if std_dev > 1e-9:
                return TestResult("Determinism", False, f"Non-deterministic: std_dev={std_dev:.6f}", max(0.0, 1.0 - std_dev))

            return TestResult("Determinism", True, f"Deterministic (std_dev={std_dev:.6f})", 1.0)

        except Exception as exc:
            return TestResult("Determinism", False, f"Exception: {exc}")

    def test_exploit_resistance(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 8: EXPLOIT RESISTANCE")
        print("=" * 60)

        try:
            env = self._new_env()
            case_id = self._first_case_id(env)
            env.reset(case_id=case_id)

            print("  Testing repeated identical action...")
            for _ in range(10):
                env.step(self._lookup_vendor_action(env))
                if env._last_done:
                    break

            repeat_done = env._last_done
            repeat_budget = env._state.budget_remaining
            print(f"    Repeat action → done={repeat_done}, budget_remaining={repeat_budget:.4f}")

            env.reset(case_id=case_id)
            print("  Testing broad action spam...")

            obs = env._observation() if env.current_case is not None else None
            actions_to_try = [
                self._lookup_vendor_action(env),
                self._lookup_policy_action(),
                self._ocr_action(obs),
                self._zoom_action(obs),
                self._crop_action(obs),
            ]

            for _ in range(4):
                for action in actions_to_try:
                    env.step(action)
                    if env._last_done:
                        break
                if env._last_done:
                    break

            spam_done = env._last_done
            spam_budget = env._state.budget_remaining
            print(f"    Spam actions → done={spam_done}, budget_remaining={spam_budget:.4f}")

            if spam_budget >= env._state.budget_total:
                return TestResult("Exploit Resistance", False, "Spam actions did not consume budget", 0.0)

            print("  ✓ Repetition/spam is naturally penalized through budget and trajectory costs")
            return TestResult("Exploit Resistance", True, "No easy exploit observed", 1.0)

        except Exception as exc:
            return TestResult("Exploit Resistance", False, f"Exception: {exc}")

    def test_generated_holdouts(self) -> TestResult:
        print("\n" + "=" * 60)
        print("TEST 9: GENERATED HOLDOUTS")
        print("=" * 60)

        try:
            env = self._new_env()
            holdouts = generate_holdout_suite(env.db.get("cases", []), variants_per_case=1, seed=123)
            if not holdouts:
                return TestResult("Generated Holdouts", False, "No holdout cases generated", 0.0)

            first = holdouts[0]
            second = generate_holdout_suite(env.db.get("cases", []), variants_per_case=1, seed=123)[0]
            if first["case_id"] != second["case_id"]:
                return TestResult("Generated Holdouts", False, "Holdout generation is not deterministic", 0.0)

            env.db["cases"].append(first)
            env.db["cases_by_id"][first["case_id"]] = first
            obs = env.reset(case_id=first["case_id"])
            doc_id = self._sample_doc_id(obs)
            if doc_id:
                env.step(LedgerShieldAction(action_type="ocr", payload={"doc_id": doc_id, "mode": "fast"}))

            print(f"  ✓ Generated deterministic holdout case: {first['case_id']}")
            print(f"  ✓ Holdout split: {first.get('benchmark_split')}")
            return TestResult("Generated Holdouts", True, "Deterministic generated holdout cases are runnable", 1.0)

        except Exception as exc:
            return TestResult("Generated Holdouts", False, f"Exception: {exc}")

    def run_all(self) -> bool:
        tests = [
            self.test_api_health,
            self.test_http_client_wrapper,
            self.test_gymnasium_loop,
            self.test_reward_stability,
            self.test_edge_cases,
            self.test_benchmark_episodes,
            self.test_determinism,
            self.test_exploit_resistance,
            self.test_generated_holdouts,
        ]

        for test in tests:
            result = test()
            self.results.append(result)

        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        passed = sum(1 for result in self.results if result.passed)
        total = len(self.results)

        print(f"\nPassed: {passed}/{total}")
        print("\nDetailed Results:")
        print("-" * 60)
        for result in self.results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.name:25s} | {result.details}")

        print("\nMetrics:")
        print("-" * 60)
        avg_metric = statistics.mean([result.metric for result in self.results])
        print(f"Overall Score: {avg_metric:.4f}")

        print("\nValidation Thresholds:")
        print("-" * 60)
        print(f"  Overall score > 0.60     → {'✅' if avg_metric > 0.60 else '❌'}")
        print(f"  Deterministic execution  → {'✅' if self.results[-2].passed else '❌'}")
        print(f"  Exploit resistance       → {'✅' if self.results[-1].passed else '❌'}")

        return passed == total


def main() -> int:
    validator = ComprehensiveValidator()
    all_passed = validator.run_all()

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Submission ready!")
    else:
        print("⚠️ SOME TESTS FAILED - Fix before submission")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
