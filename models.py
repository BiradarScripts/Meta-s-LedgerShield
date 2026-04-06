from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from openenv_compat import Action, Observation, State
from pydantic import BaseModel, Field

InvestigationActionType = Literal[
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
]

InterventionActionType = Literal[
    "request_callback_verification",
    "freeze_vendor_profile",
    "request_bank_change_approval_chain",
    "request_po_reconciliation",
    "request_additional_receipt_evidence",
    "route_to_procurement",
    "route_to_security",
    "flag_duplicate_cluster_review",
    "create_human_handoff",
]

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
    "request_callback_verification",
    "freeze_vendor_profile",
    "request_bank_change_approval_chain",
    "request_po_reconciliation",
    "request_additional_receipt_evidence",
    "route_to_procurement",
    "route_to_security",
    "flag_duplicate_cluster_review",
    "create_human_handoff",
    "submit_decision",
]

DecisionType = Literal["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"]
TaskType = Literal["task_a", "task_b", "task_c", "task_d"]


class LedgerShieldReward(BaseModel):
    value: float
    terminal: bool = False
    components: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    message: str = ""
    novel_signal_count: int = 0
    revealed_artifact_ids: list[str] = field(default_factory=list)


@dataclass
class CaseDecision:
    case_id: str
    decision: DecisionType
    risk_score: float = 0.0
    confidence: float = 0.5
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
    recommended_next_action: str = ""
    handoff_packet: dict[str, Any] = field(default_factory=dict)
    intervention_log: list[dict[str, Any]] = field(default_factory=list)


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
    revealed_artifacts: list[dict[str, Any]] = field(default_factory=list)
    pending_events: list[dict[str, Any]] = field(default_factory=list)
    budget_remaining: float = 0.0
    budget_total: float = 0.0
    step_count: int = 0
    max_steps: int = 0
    case_clock: int = 0
    risk_snapshot: dict[str, Any] = field(default_factory=dict)
    investigation_status: dict[str, Any] = field(default_factory=dict)
    last_tool_result: dict[str, Any] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    available_interventions: list[str] = field(default_factory=list)
    case_metadata: dict[str, Any] = field(default_factory=dict)
    portfolio_context: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerShieldState(State):
    episode_id: str = ""
    case_id: str = ""
    task_type: str = ""
    budget_total: float = 15.0
    budget_remaining: float = 15.0
    max_steps: int = 20
    step_count: int = 0
    case_clock: int = 0
    submitted: bool = False
    final_score: float = 0.0
    unsafe_outcome: bool = False
    visible_doc_ids: list[str] = field(default_factory=list)
    revealed_artifact_ids: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    interventions_taken: list[dict[str, Any]] = field(default_factory=list)
    observed_risk_signals: list[str] = field(default_factory=list)
    final_outcome: dict[str, Any] = field(default_factory=dict)
    handoff_packet: dict[str, Any] = field(default_factory=dict)
    pending_event_ids: list[str] = field(default_factory=list)
    portfolio_metrics: dict[str, Any] = field(default_factory=dict)
    decision_readiness: float = 0.0
    difficulty: str = "medium"
    terminal_reason: str = ""
