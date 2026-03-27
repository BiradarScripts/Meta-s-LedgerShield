from __future__ import annotations
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Literal
from pydantic import Field

# Make sure openenv is installed: pip install openenv
from openenv.core.env_server import Action, Observation, State

ActionType = Literal[
    "zoom",
    "ocr",
    "lookup_vendor",
    "lookup_po",
    "lookup_receipt",
    "search_ledger",
    "submit_decision",
]
DecisionType = Literal["PAY", "HOLD", "NEEDS_REVIEW"]
TaskType = Literal["task_a", "task_b", "task_c"]

# These don't inherit from OpenEnv, so standard @dataclass is perfect here
@dataclass
class ToolResult:
    tool_name: str
    success: bool
    payload: dict[str, Any] = dataclass_field(default_factory=dict)
    cost: float = 0.0
    message: str = ""

@dataclass
class CaseDecision:
    case_id: str
    decision: DecisionType
    extracted_fields: dict[str, Any] = dataclass_field(default_factory=dict)
    line_items: list[dict[str, Any]] = dataclass_field(default_factory=list)
    discrepancies: list[str] = dataclass_field(default_factory=list)
    duplicate_links: list[str] = dataclass_field(default_factory=list)
    fraud_flags: list[str] = dataclass_field(default_factory=list)
    evidence_map: dict[str, Any] = dataclass_field(default_factory=dict)
    notes: str = ""

# REMOVED @dataclass here. These are pure Pydantic models now.
class LedgerShieldAction(Action):
    action_type: ActionType
    payload: dict[str, Any] = Field(default_factory=dict)

class LedgerShieldObservation(Observation):
    case_id: str = ""
    task_type: str = ""
    instruction: str = ""
    visible_documents: list[dict[str, Any]] = Field(default_factory=list)
    budget_remaining: float = 0.0
    step_count: int = 0
    last_tool_result: dict[str, Any] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)

class LedgerShieldState(State):
    case_id: str = ""
    task_type: str = ""
    budget_total: float = 15.0
    budget_remaining: float = 15.0
    max_steps: int = 20
    revealed_docs: list[str] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    submitted: bool = False
    final_score: float = 0.0
    unsafe_outcome: bool = False
    gold_summary: dict[str, Any] = Field(default_factory=dict)