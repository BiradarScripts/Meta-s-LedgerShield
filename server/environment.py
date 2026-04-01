from __future__ import annotations

from dataclasses import asdict
import random
import uuid
from typing import Any

from models import LedgerShieldObservation, LedgerShieldState
from openenv_compat import Environment

from .data_loader import load_all
from .grading import score_submission
from .outcome_simulator import simulate_outcome
from .risk_rules import assess_submission_risk
from .schema import ALLOWED_ACTIONS, ALLOWED_DECISIONS, INTERVENTION_ACTIONS
from .tools import (
    compare_bank_account_tool,
    get_doc_crop_tool,
    inspect_email_thread_tool,
    lookup_po_tool,
    lookup_policy_tool,
    lookup_receipt_tool,
    lookup_vendor_history_tool,
    lookup_vendor_tool,
    ocr_tool,
    search_ledger_tool,
    zoom_tool,
)
from .transition_engine import handle_intervention, normalized_result_with_signals
from .world_state import (
    build_hidden_world,
    investigation_status,
    public_revealed_artifacts,
    risk_snapshot,
)

TOOL_COSTS = {
    "zoom": 0.20,
    "get_doc_crop": 0.20,
    "ocr_fast": 0.45,
    "ocr_accurate": 1.10,
    "lookup_vendor": 0.20,
    "lookup_vendor_history": 0.25,
    "lookup_policy": 0.15,
    "lookup_po": 0.20,
    "lookup_receipt": 0.20,
    "search_ledger": 0.35,
    "inspect_email_thread": 0.25,
    "compare_bank_account": 0.15,
    "request_callback_verification": 0.40,
    "freeze_vendor_profile": 0.20,
    "request_bank_change_approval_chain": 0.30,
    "request_po_reconciliation": 0.30,
    "request_additional_receipt_evidence": 0.25,
    "route_to_procurement": 0.15,
    "route_to_security": 0.20,
    "flag_duplicate_cluster_review": 0.25,
    "create_human_handoff": 0.20,
    "submit_decision": 0.0,
}


class LedgerShieldEnvironment(Environment):
    def __init__(self) -> None:
        super().__init__()
        self.db = load_all()
        self.rng = random.Random(42)
        self.current_case: dict[str, Any] | None = None
        self._state = LedgerShieldState()
        self._last_reward = 0.0
        self._last_done = False
        self._last_info: dict[str, Any] = {}
        self._hidden_world: dict[str, Any] = {}

    @property
    def state(self) -> LedgerShieldState:
        return self._state

    def _select_case(self, seed: int | None = None, case_id: str | None = None) -> dict[str, Any]:
        if case_id:
            case = self.db["cases_by_id"].get(case_id)
            if case is None:
                raise ValueError(f"unknown case_id: {case_id}")
            return case
        rng = random.Random(seed) if seed is not None else self.rng
        return rng.choice(self.db["cases"])

    def _initial_visible_doc_ids(self) -> list[str]:
        assert self.current_case is not None
        doc_ids = self.current_case.get("initial_visible_doc_ids") or [
            doc.get("doc_id")
            for doc in self.current_case.get("documents", [])
            if doc.get("doc_id")
        ]
        return [str(doc_id) for doc_id in doc_ids]

    def _visible_document_catalog(self) -> list[dict[str, Any]]:
        assert self.current_case is not None
        docs: list[dict[str, Any]] = []
        visible_set = set(self._state.visible_doc_ids)

        for doc in self.current_case.get("documents", []):
            doc_id = str(doc.get("doc_id"))
            if doc_id not in visible_set:
                continue

            docs.append(
                {
                    "doc_id": doc_id,
                    "doc_type": doc.get("doc_type", "unknown"),
                    "thumbnail": doc.get("thumbnail", f"thumbnail::{doc_id}"),
                    "page_count": doc.get("page_count", 1),
                    "language": doc.get("language", "en"),
                    "available_views": [
                        "thumbnail",
                        "zoom",
                        "get_doc_crop",
                        "ocr_fast",
                        "ocr_accurate",
                    ],
                }
            )
        return docs

    def _observation(
        self,
        tool_result: dict[str, Any] | None = None,
        messages: list[str] | None = None,
    ) -> LedgerShieldObservation:
        assert self.current_case is not None
        return LedgerShieldObservation(
            case_id=self._state.case_id,
            task_type=self._state.task_type,
            instruction=self.current_case["instruction"],
            visible_documents=self._visible_document_catalog(),
            revealed_artifacts=public_revealed_artifacts(self._state, self._hidden_world),
            budget_remaining=round(self._state.budget_remaining, 3),
            budget_total=round(self._state.budget_total, 3),
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            case_clock=self._state.case_clock,
            risk_snapshot=risk_snapshot(self._state, self._hidden_world),
            investigation_status=investigation_status(self._state),
            last_tool_result=tool_result or {},
            messages=messages or [],
            allowed_actions=list(ALLOWED_ACTIONS),
            available_interventions=list(INTERVENTION_ACTIONS),
            case_metadata={
                "difficulty": self.current_case.get("difficulty", "medium"),
                "task_label": self.current_case.get("task_label", ""),
            },
        )

    def reset(self, seed: int | None = None, case_id: str | None = None) -> LedgerShieldObservation:
        self.current_case = self._select_case(seed=seed, case_id=case_id)
        self._hidden_world = build_hidden_world(self.current_case)

        self._state = LedgerShieldState(
            episode_id=str(uuid.uuid4()),
            case_id=self.current_case["case_id"],
            task_type=self.current_case["task_type"],
            budget_total=self.current_case.get("budget_total", 15.0),
            budget_remaining=self.current_case.get("budget_total", 15.0),
            max_steps=self.current_case.get("max_steps", 20),
            visible_doc_ids=self._initial_visible_doc_ids(),
            difficulty=self.current_case.get("difficulty", "medium"),
            hidden_risk_signals=list(self._hidden_world.get("hidden_risk_signals", [])),
        )

        self._last_reward = 0.0
        self._last_done = False
        self._last_info = {"case_id": self._state.case_id}

        return self._observation(messages=[f"Loaded case {self._state.case_id}"])

    def _apply_cost(self, tool_name: str, payload: dict[str, Any]) -> float:
        if tool_name == "ocr":
            return TOOL_COSTS["ocr_accurate"] if payload.get("mode", "fast") == "accurate" else TOOL_COSTS["ocr_fast"]
        return TOOL_COSTS.get(tool_name, 0.0)

    def _dispatch_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.current_case is not None

        if tool_name == "zoom":
            return zoom_tool(self.current_case, payload)
        if tool_name == "get_doc_crop":
            return get_doc_crop_tool(self.current_case, payload)
        if tool_name == "ocr":
            return ocr_tool(self.current_case, payload)
        if tool_name == "lookup_vendor":
            return lookup_vendor_tool(self.db["vendors_by_key"], payload)
        if tool_name == "lookup_vendor_history":
            return lookup_vendor_history_tool(self.db["vendor_history"], payload)
        if tool_name == "lookup_policy":
            return lookup_policy_tool(self.db["policy_by_id"], self.db["policy_rules"], payload)
        if tool_name == "lookup_po":
            return lookup_po_tool(self.db["po_by_id"], payload)
        if tool_name == "lookup_receipt":
            return lookup_receipt_tool(self.db["receipt_by_id"], payload)
        if tool_name == "search_ledger":
            return search_ledger_tool(self.db["ledger_index"], payload)
        if tool_name == "inspect_email_thread":
            return inspect_email_thread_tool(self.db["email_threads"], payload)
        if tool_name == "compare_bank_account":
            return compare_bank_account_tool(self.db["vendors_by_key"], payload)

        return {"error": f"unknown action_type: {tool_name}"}

    def _handle_intervention(
        self,
        action_type: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        return handle_intervention(
            state=self._state,
            hidden_world=self._hidden_world,
            action_type=action_type,
            payload=payload,
        )

    def _normalize_tool_result(
        self,
        tool_name: str,
        raw: dict[str, Any],
        cost: float,
    ) -> tuple[dict[str, Any], list[str]]:
        return normalized_result_with_signals(
            state=self._state,
            tool_name=tool_name,
            raw=raw,
            cost=cost,
        )

    def _investigation_summary(self) -> dict[str, Any]:
        return {
            "tool_calls": len(self._state.tool_trace),
            "interventions_taken": len(self._state.interventions_taken),
            "revealed_artifact_ids": list(self._state.revealed_artifact_ids),
            "observed_risk_signals": list(self._state.observed_risk_signals),
        }

    def step(self, action: Any) -> LedgerShieldObservation:
        if self.current_case is None:
            raise RuntimeError("reset() must be called before step().")

        if self._last_done:
            return self._observation(messages=["Episode already complete."])

        payload = getattr(action, "payload", {}) or {}
        action_type = getattr(action, "action_type", "")

        self._state.step_count += 1
        self._state.case_clock += 1

        if action_type not in ALLOWED_ACTIONS:
            self._last_reward = -0.05
            self._last_done = False
            self._last_info = {"error": f"Action not allowed: {action_type}"}
            return self._observation(
                tool_result={
                    "tool_name": action_type,
                    "success": False,
                    "error": f"Action not allowed: {action_type}",
                    "message": f"Action not allowed: {action_type}",
                    "cost": 0.0,
                },
                messages=[f"Action not allowed: {action_type}"],
            )

        done = False
        reward = 0.0
        info: dict[str, Any] = {}

        if action_type == "submit_decision":
            submitted = dict(payload)
            decision = submitted.get("decision")

            if decision not in ALLOWED_DECISIONS:
                self._last_reward = -0.25
                self._last_done = False
                self._last_info = {"error": f"Invalid decision: {decision}"}
                return self._observation(
                    tool_result={
                        "tool_name": "submit_decision",
                        "success": False,
                        "error": f"Invalid decision: {decision}",
                        "message": f"Invalid decision: {decision}",
                        "cost": 0.0,
                    },
                    messages=[f"Invalid decision: {decision}"],
                )

            budget_used = max(self._state.budget_total - self._state.budget_remaining, 0.0)
            budget_penalty = (budget_used / max(self._state.budget_total, 1.0)) * 0.12

            outcome = simulate_outcome(
                submitted=submitted,
                trajectory=self._state.trajectory,
                hidden_world=self._hidden_world,
            )

            final_score, breakdown = score_submission(
                task_type=self._state.task_type,
                submitted=submitted,
                gold=self.current_case["gold"],
                budget_penalty=budget_penalty,
                trajectory=self._state.trajectory,
                outcome=outcome,
                investigation_summary=self._investigation_summary(),
            )

            heuristic_risk, triggered = assess_submission_risk(
                submitted=submitted,
                gold=self.current_case["gold"],
                trajectory=self._state.trajectory,
                revealed_artifacts=public_revealed_artifacts(self._state, self._hidden_world),
            )

            self._state.final_score = final_score
            self._state.submitted = True
            self._state.final_outcome = outcome
            self._state.unsafe_outcome = bool(outcome.get("unsafe_payment"))
            self._state.terminal_reason = "decision_submitted"

            done = True
            reward = final_score

            result = {
                "tool_name": "submit_decision",
                "success": True,
                "submission_received": True,
                "final_score": final_score,
                "score_breakdown": breakdown,
                "risk_assessment": heuristic_risk,
                "triggered_risk_reasons": triggered,
                "unsafe_outcome": self._state.unsafe_outcome,
                "decision": decision,
                "outcome": outcome,
                "message": "Decision submitted and graded.",
                "cost": 0.0,
            }

            info = {
                "final_score": final_score,
                "score_breakdown": breakdown,
                "unsafe_outcome": self._state.unsafe_outcome,
                "outcome": outcome,
            }
            cost = 0.0
            messages = ["Decision submitted and graded."]

        elif action_type in INTERVENTION_ACTIONS:
            cost = self._apply_cost(action_type, payload)

            observed_before = len(self._state.observed_risk_signals)
            raw_result, messages = self._handle_intervention(action_type, payload)
            result, _ = self._normalize_tool_result(action_type, raw_result, cost)

            observed_after = len(self._state.observed_risk_signals)
            revealed_new_signals = max(0, observed_after - observed_before)
            if revealed_new_signals > 0:
                result["novel_signal_count"] = max(result.get("novel_signal_count", 0), revealed_new_signals)

            reward = -cost * 0.03 + (0.04 if result.get("novel_signal_count", 0) > 0 else 0.0)
            info = {
                "tool_name": action_type,
                "success": result["success"],
                "intervention": True,
            }

        else:
            raw_result = self._dispatch_tool(action_type, payload)
            cost = self._apply_cost(action_type, payload)
            result, messages = self._normalize_tool_result(action_type, raw_result, cost)

            reward = -cost * 0.05
            if result.get("novel_signal_count", 0) > 0:
                reward += min(0.06, 0.02 * result["novel_signal_count"])
            if not result["success"]:
                reward -= 0.05

            info = {
                "tool_name": action_type,
                "success": result["success"],
            }

        self._state.budget_remaining = round(max(self._state.budget_remaining - cost, 0.0), 4)

        trajectory_entry = {
            "step": self._state.step_count,
            "case_clock": self._state.case_clock,
            "action_type": action_type,
            "payload": payload,
            "cost": cost,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "is_intervention": action_type in INTERVENTION_ACTIONS,
        }

        self._state.tool_trace.append(
            {
                "step": self._state.step_count,
                "tool": action_type,
                "payload": payload,
                "cost": cost,
                "result": result,
            }
        )
        self._state.trajectory.append(trajectory_entry)

        if self._state.step_count >= self._state.max_steps and not done:
            done = True
            self._state.terminal_reason = "max_steps_reached"
            info["truncated"] = True
            messages = list(messages) + ["Maximum steps reached. Episode terminated."]

        if self._state.budget_remaining <= 0 and not done:
            done = True
            self._state.terminal_reason = "budget_exhausted"
            info["budget_exhausted"] = True
            messages = list(messages) + ["Budget exhausted. Episode terminated."]

        obs = self._observation(tool_result=result, messages=messages)
        self._last_reward = reward
        self._last_done = done
        self._last_info = info
        return obs

    def result_payload(self, observation: LedgerShieldObservation) -> dict[str, Any]:
        return {
            "observation": asdict(observation),
            "reward": self._last_reward,
            "done": self._last_done,
            "info": self._last_info,
        }