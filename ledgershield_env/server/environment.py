from __future__ import annotations
import random
import uuid
from typing import Any

from openenv.core.env_server import Environment
from ..models import LedgerShieldObservation, LedgerShieldState
from .data_loader import load_all
from .grading import score_submission
from .tools import (
    lookup_po_tool,
    lookup_receipt_tool,
    lookup_vendor_tool,
    ocr_tool,
    search_ledger_tool,
    zoom_tool,
)

TOOL_COSTS = {
    "zoom": 0.3,
    "ocr_fast": 0.5,
    "ocr_accurate": 1.2,
    "lookup_vendor": 0.2,
    "lookup_po": 0.2,
    "lookup_receipt": 0.2,
    "search_ledger": 0.4,
    "submit_decision": 0.0,
}

class LedgerShieldEnvironment(Environment):
    def __init__(self) -> None:
        super().__init__()
        self.db = load_all()
        self.rng = random.Random(42)
        self.current_case: dict[str, Any] | None = None
        
        # Explicitly pass default values to satisfy the strict base class
        self._state = LedgerShieldState(
            case_id="",
            task_type="",
            budget_total=15.0,
            budget_remaining=15.0,
            max_steps=20,
            revealed_docs=[],
            tool_trace=[],
            submitted=False,
            final_score=0.0,
            unsafe_outcome=False,
            gold_summary={}
        )
        
        self._last_reward = 0.0
        self._last_done = False
        self._last_info: dict[str, Any] = {}

    @property
    def state(self) -> LedgerShieldState:
        return self._state

    def _select_case(self, seed: int | None = None) -> dict[str, Any]:
        cases = self.db["cases"]
        rng = random.Random(seed) if seed is not None else self.rng
        return rng.choice(cases)

    def _observation(self, tool_result: dict[str, Any] | None = None, messages: list[str] | None = None) -> LedgerShieldObservation:
        assert self.current_case is not None
        visible_documents = []
        for doc in self.current_case.get("documents", []):
            visible_documents.append({
                "doc_id": doc["doc_id"],
                "doc_type": doc["doc_type"],
                "thumbnail": doc.get("thumbnail", f"thumbnail::{doc['doc_id']}"),
                "available_views": ["thumbnail", "ocr_fast", "ocr_accurate", "zoom"],
            })
            
        return LedgerShieldObservation(
            case_id=self._state.case_id,
            task_type=self._state.task_type,
            instruction=self.current_case["instruction"],
            visible_documents=visible_documents,
            budget_remaining=round(self._state.budget_remaining, 3),
            step_count=self._state.step_count,
            last_tool_result=tool_result or {},
            messages=messages or [],
            allowed_actions=list(TOOL_COSTS.keys()),
        )

    def reset(self, seed: int | None = None) -> LedgerShieldObservation:
        self.current_case = self._select_case(seed)
        gold = self.current_case["gold"]
        budget_total = self.current_case.get("budget_total", 15.0)
        
        self._state = LedgerShieldState(
            case_id=self.current_case["case_id"],
            task_type=self.current_case["task_type"],
            budget_total=budget_total,
            budget_remaining=budget_total,
            max_steps=self.current_case.get("max_steps", 20),
            revealed_docs=[],
            tool_trace=[],
            submitted=False,
            final_score=0.0,
            unsafe_outcome=False,
            gold_summary=gold,
        )
        return self._observation(messages=["LedgerShield case loaded."])

    def step(self, action) -> LedgerShieldObservation:
        if self.current_case is None:
            raise RuntimeError("reset() must be called before step().")
            
        self._state.step_count += 1
        tool_name = action.action_type
        payload = action.payload or {}
        
        reward = 0.0
        done = False
        info: dict[str, Any] = {}
        result: dict[str, Any] = {}
        cost = TOOL_COSTS.get(tool_name, 0.0)

        if tool_name == "zoom":
            result = zoom_tool(self.current_case, payload)
        elif tool_name == "ocr":
            result = ocr_tool(self.current_case, payload)
            cost = TOOL_COSTS["ocr_accurate"] if payload.get("mode") == "accurate" else TOOL_COSTS["ocr_fast"]
        elif tool_name == "lookup_vendor":
            result = lookup_vendor_tool(self.db["vendors"], payload)
        elif tool_name == "lookup_po":
            result = lookup_po_tool(self.db["po_records"], payload)
        elif tool_name == "lookup_receipt":
            result = lookup_receipt_tool(self.db["receipts"], payload)
        elif tool_name == "search_ledger":
            result = search_ledger_tool(self.db["ledger_index"], payload)
        elif tool_name == "submit_decision":
            submitted = payload
            budget_penalty = max(self._state.budget_total - self._state.budget_remaining, 0.0) / max(self._state.budget_total, 1.0) * 0.2
            
            final_score, breakdown = score_submission(
                task_type=self._state.task_type,
                submitted=submitted,
                gold=self.current_case["gold"],
                budget_penalty=budget_penalty,
            )
            
            self._state.final_score = final_score
            self._state.submitted = True
            done = True
            reward = final_score
            
            result = {
                "submission_received": True,
                "final_score": final_score,
                "breakdown": breakdown,
            }
            
            if submitted.get("decision") == "PAY" and self.current_case["gold"].get("unsafe_if_pay", False):
                self._state.unsafe_outcome = True
                reward = max(reward - 0.5, 0.0)
                result["unsafe_outcome"] = True
                
            info = {"final_score": self._state.final_score, "breakdown": breakdown}
            
        else:
            result = {"error": f"unknown action_type: {tool_name}"}
            reward = -0.05

        self._state.budget_remaining -= cost
        self._state.tool_trace.append({
            "step": self._state.step_count,
            "tool": tool_name,
            "payload": payload,
            "cost": cost,
            "result": result,
        })
        
        if tool_name != "submit_decision":
            reward -= cost * 0.05
            
        if self._state.step_count >= self._state.max_steps:
            done = True
            info["truncated"] = True
            
        if self._state.budget_remaining <= 0:
            done = True
            info["budget_exhausted"] = True
            
        obs = self._observation(tool_result=result)
        self._last_reward = reward
        self._last_done = done
        self._last_info = info
        return obs

    def result_payload(self, observation: LedgerShieldObservation) -> dict[str, Any]:
        return {
            "observation": observation.__dict__,
            "reward": self._last_reward,
            "done": self._last_done,
            "info": self._last_info,
        }