from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from openenv_compat import Action, Observation, State

ActionType = Literal[
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
]

DecisionType = Literal["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"]
TaskType = Literal["task_a", "task_b", "task_c", "task_d"]


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    message: str = ""


@dataclass
class CaseDecision:
    case_id: str
    decision: DecisionType
    risk_score: float = 0.0
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    line_items: list[dict[str, Any]] = field(default_factory=list)
    discrepancies: list[str] = field(default_factory=list)
    duplicate_links: list[str] = field(default_factory=list)
    fraud_flags: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    policy_checks: dict[str, str] = field(default_factory=dict)
    evidence_map: dict[str, Any] = field(default_factory=dict)
    counterfactual: str = ""
    notes: str = ""


@dataclass
class LedgerShieldAction(Action):
    action_type: ActionType
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerShieldObservation(Observation):
    case_id: str = ""
    task_type: str = ""
    instruction: str = ""
    visible_documents: list[dict[str, Any]] = field(default_factory=list)
    budget_remaining: float = 0.0
    step_count: int = 0
    last_tool_result: dict[str, Any] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    case_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerShieldState(State):
    case_id: str = ""
    task_type: str = ""
    budget_total: float = 15.0
    budget_remaining: float = 15.0
    max_steps: int = 20
    submitted: bool = False
    final_score: float = 0.0
    unsafe_outcome: bool = False
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    visible_doc_ids: list[str] = field(default_factory=list)
    difficulty: str = "medium"
