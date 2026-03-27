from __future__ import annotations

from dataclasses import asdict
import random
import uuid
from typing import Any

from ..models import LedgerShieldObservation, LedgerShieldState
from ..openenv_compat import Environment
from .data_loader import load_all
from .grading import score_submission
from .risk_rules import assess_submission_risk
from .tools import (
    compare_bank_account_tool,
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

    @property
    def state(self) -> LedgerShieldState:
        return self._state

    def _select_case(self, seed: int | None = None, case_id: str | None = None) -> dict[str, Any]:
        cases = self.db["cases"]
        if case_id:
            for case in cases:
                if case["case_id"] == case_id:
                    return case
            raise ValueError(f"unknown case_id: {case_id}")
        rng = random.Random(seed) if seed is not None else self.rng
        return rng.choice(cases)

    def _visible_document_catalog(self) -> list[dict[str, Any]]:
        assert self.current_case is not None
        docs = []
        for doc in self.current_case.get("documents", []):
            docs.append(
                {
                    "doc_id": doc["doc_id"],
                    "doc_type": doc["doc_type"],
                    "thumbnail": doc.get("thumbnail", f"thumbnail::{doc['doc_id']}"),
                    "page_count": doc.get("page_count", 1),
                    "language": doc.get("language", "en"),
                    "available_views": ["thumbnail", "ocr_fast", "ocr_accurate", "zoom"],
                }
            )
        return docs

    def _observation(self, tool_result: dict[str, Any] | None = None, messages: list[str] | None = None) -> LedgerShieldObservation:
        assert self.current_case is not None
        return LedgerShieldObservation(
            case_id=self._state.case_id,
            task_type=self._state.task_type,
            instruction=self.current_case["instruction"],
            visible_documents=self._visible_document_catalog(),
            budget_remaining=round(self._state.budget_remaining, 3),
            step_count=self._state.step_count,
            last_tool_result=tool_result or {},
            messages=messages or [],
            allowed_actions=[
                "zoom",
                "get_doc_crop",
                "ocr",
                "lookup_vendor",
                "lookup_vendor_history",
                "lookup_policy",
                "lookup_po",
                "lookup_receipt",
                "search_ledger",
                "inspect_email_thread",
                "compare_bank_account",
                "submit_decision",
            ],
            case_metadata={
                "difficulty": self.current_case.get("difficulty", "medium"),
                "task_label": self.current_case.get("task_label", ""),
            },
        )

    def reset(self, seed: int | None = None, case_id: str | None = None) -> LedgerShieldObservation:
        self.current_case = self._select_case(seed=seed, case_id=case_id)
        self._state = LedgerShieldState(
            episode_id=str(uuid.uuid4()),
            case_id=self.current_case["case_id"],
            task_type=self.current_case["task_type"],
            budget_total=self.current_case.get("budget_total", 15.0),
            budget_remaining=self.current_case.get("budget_total", 15.0),
            max_steps=self.current_case.get("max_steps", 20),
            visible_doc_ids=[doc["doc_id"] for doc in self.current_case.get("documents", [])],
            difficulty=self.current_case.get("difficulty", "medium"),
        )
        self._last_reward = 0.0
        self._last_done = False
        self._last_info = {"case_id": self._state.case_id}
        return self._observation(messages=["LedgerShield case loaded."])

    def _apply_cost(self, tool_name: str, payload: dict[str, Any]) -> float:
        if tool_name == "ocr":
            return TOOL_COSTS["ocr_accurate"] if payload.get("mode", "fast") == "accurate" else TOOL_COSTS["ocr_fast"]
        return TOOL_COSTS.get(tool_name, 0.0)

    def _dispatch_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.current_case is not None
        if tool_name in {"zoom", "get_doc_crop"}:
            return zoom_tool(self.current_case, payload)
        if tool_name == "ocr":
            return ocr_tool(self.current_case, payload)
        if tool_name == "lookup_vendor":
            return lookup_vendor_tool(self.db["vendors"], payload)
        if tool_name == "lookup_vendor_history":
            return lookup_vendor_history_tool(self.db["vendor_history"], payload)
        if tool_name == "lookup_policy":
            return lookup_policy_tool(self.db["policy_rules"], payload)
        if tool_name == "lookup_po":
            return lookup_po_tool(self.db["po_records"], payload)
        if tool_name == "lookup_receipt":
            return lookup_receipt_tool(self.db["receipts"], payload)
        if tool_name == "search_ledger":
            return search_ledger_tool(self.db["ledger_index"], payload)
        if tool_name == "inspect_email_thread":
            return inspect_email_thread_tool(self.db["email_threads"], payload)
        if tool_name == "compare_bank_account":
            return compare_bank_account_tool(self.db["vendors"], payload)
        return {"error": f"unknown action_type: {tool_name}"}

    def step(self, action: Any) -> LedgerShieldObservation:
        if self.current_case is None:
            raise RuntimeError("reset() must be called before step().")

        self._state.step_count += 1
        payload = getattr(action, "payload", {}) or {}
        tool_name = getattr(action, "action_type", "")

        done = False
        reward = 0.0
        info: dict[str, Any] = {}
        if tool_name == "submit_decision":
            submitted = payload
            budget_used = max(self._state.budget_total - self._state.budget_remaining, 0.0)
            budget_penalty = (budget_used / max(self._state.budget_total, 1.0)) * 0.15
            final_score, breakdown = score_submission(
                task_type=self._state.task_type,
                submitted=submitted,
                gold=self.current_case["gold"],
                budget_penalty=budget_penalty,
            )
            heuristic_risk, triggered = assess_submission_risk(submitted, self.current_case["gold"])
            self._state.final_score = final_score
            self._state.submitted = True
            done = True
            reward = final_score
            result = {
                "submission_received": True,
                "final_score": final_score,
                "breakdown": breakdown,
                "risk_assessment": heuristic_risk,
                "triggered_risk_reasons": triggered,
            }
            if submitted.get("decision") == "PAY" and self.current_case["gold"].get("unsafe_if_pay", False):
                self._state.unsafe_outcome = True
                reward = max(reward - 0.5, 0.0)
                result["unsafe_outcome"] = True
            info = {"final_score": final_score, "breakdown": breakdown}
            cost = TOOL_COSTS["submit_decision"]
        else:
            result = self._dispatch_tool(tool_name, payload)
            cost = self._apply_cost(tool_name, payload)
            reward = -cost * 0.05
            if "error" in result:
                reward -= 0.05

        self._state.budget_remaining = round(max(self._state.budget_remaining - cost, 0.0), 4)
        self._state.tool_trace.append(
            {
                "step": self._state.step_count,
                "tool": tool_name,
                "payload": payload,
                "cost": cost,
                "result": result,
            }
        )

        if self._state.step_count >= self._state.max_steps and not done:
            done = True
            info["truncated"] = True
        if self._state.budget_remaining <= 0 and not done:
            done = True
            info["budget_exhausted"] = True

        obs = self._observation(tool_result=result)
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
