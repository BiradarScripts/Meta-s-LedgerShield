"""
Data models for LedgerShield.

Defines the core dataclasses and Pydantic models used throughout the
LedgerShield benchmark, including:

- **Type aliases**: Domain-specific Literal types for actions, decisions,
  and task families.
- **LedgerShieldReward**: Pydantic model for structured reward payloads.
- **ToolResult**: Result of a single tool invocation.
- **CaseDecision**: Agent's final decision submission.
- **LedgerShieldAction**: Gymnasium-style action (action_type + payload).
- **LedgerShieldObservation**: Full observation at each step.
- **LedgerShieldState**: Internal episode state (not visible to agent).

TypedDict Internal Returns (Phase 4.5):
    StepResultDict and ScoreBreakdownDict provide formalized typing
    for internal return values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from openenv_compat import Action, Observation, State
from dataclasses import dataclass

# ── Type aliases ─────────────────────────────────────────────────────────────

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
TaskType = Literal["task_a", "task_b", "task_c", "task_d", "task_e"]


# ── TypedDict for internal returns (Phase 4.5) ──────────────────────────────

class StepResultDict(TypedDict, total=False):
    """Typed dictionary for step() return payloads."""
    observation: dict[str, Any]
    reward: float
    done: bool
    truncated: bool
    terminated: bool
    info: dict[str, Any]


class ScoreBreakdownDict(TypedDict, total=False):
    """Typed dictionary for score_submission() breakdown."""
    field_score: float
    line_item_score: float
    evidence_score: float
    decision_score: float
    discrepancy_score: float
    duplicate_score: float
    fraud_score: float
    reason_score: float
    policy_score: float
    counterfactual_score: float
    investigation_score: float
    intervention_score: float
    resolution_state_score: float
    calibration_score: float
    efficiency_score: float
    outcome_score: float
    pressure_event_score: float
    callback_interpretation_score: float
    cross_invoice_link_score: float
    campaign_detection_score: float
    proper_score: float
    brier_score: float
    log_score: float
    penalized_brier_score: float
    causal_score: float
    causal_association_score: float
    causal_intervention_score: float
    d_separation_score: float
    compliance_score: float
    compliance_adjustment: float
    compliance_penalty: float
    currency_validation_score: float
    currency_adjustment: float
    cross_invoice_link_matches: float
    counterfactual_doc_refs: float
    certificate_score: float
    certificate_validity_score: float
    certificate_support_score: float
    certificate_stability_score: float
    certificate_minimality_score: float
    certificate_unsupported_claim_rate: float
    certificate_adjustment: float
    institutional_loss_score: float
    degenerate_penalty: float
    error: float


# ── Reward model (lightweight dataclass fallback) ──────────────────────────

@dataclass
class LedgerShieldReward:
    """Structured reward payload returned at each step.

    This lightweight dataclass replaces the previous Pydantic model when
    Pydantic is not available in the runtime. It provides the same fields
    and default factories used throughout the codebase.
    """
    value: float = 0.0
    terminal: bool = False
    components: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Provide a Pydantic-compatible serialization shim used in some runtime
    # paths. The project previously relied on BaseModel.model_dump(), so
    # offer a lightweight equivalent to avoid runtime errors when Pydantic
    # is not installed.
    def model_dump(self) -> dict[str, Any]:
        return {
            "value": float(self.value),
            "terminal": bool(self.terminal),
            "components": dict(self.components or {}),
            "metadata": dict(self.metadata or {}),
        }


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """Result of a single tool invocation.

    Attributes:
        tool_name: Name of the tool that was called.
        success: Whether the call succeeded.
        payload: Returned data from the tool.
        cost: Budget cost of the call.
        message: Human-readable result message.
        novel_signal_count: New risk signals discovered by this call.
        revealed_artifact_ids: Artifact IDs revealed by this call.
    """
    tool_name: str
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    message: str = ""
    novel_signal_count: int = 0
    revealed_artifact_ids: list[str] = field(default_factory=list)


@dataclass
class CaseDecision:
    """Agent's final decision submission for a case.

    Contains all the structured outputs the agent must produce,
    including the decision, supporting evidence, risk assessments,
    policy checks, and counterfactual reasoning.

    Attributes:
        case_id: The case being decided.
        decision: One of PAY, HOLD, NEEDS_REVIEW, ESCALATE_FRAUD.
        risk_score: Agent's assessed risk level (0.0–1.0).
        confidence: Agent's confidence in its decision (0.0–1.0).
        extracted_fields: Key-value pairs extracted from documents.
        line_items: Itemized list of invoice line items.
        discrepancies: List of identified discrepancies.
        duplicate_links: IDs of potential duplicate invoices.
        fraud_flags: Identified fraud indicator types.
        reason_codes: Canonical reason codes for the decision.
        policy_checks: Policy verification results.
        evidence_map: Evidence references keyed by claim type.
        predicted_probabilities: Probability distribution over latent hypotheses.
        counterfactual: Hypothetical alternative scenario analysis.
        decision_certificate: Machine-checkable proof graph tying evidence,
            policies, hypotheses, interventions, and counterfactuals to the
            payment decision.
        notes: Free-text investigation notes.
        recommended_next_action: Suggested follow-up action.
        handoff_packet: Structured data for human handoff.
        intervention_log: Record of intervention actions taken.
    """
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
    predicted_probabilities: dict[str, float] = field(default_factory=dict)
    counterfactual: str = ""
    decision_certificate: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    recommended_next_action: str = ""
    handoff_packet: dict[str, Any] = field(default_factory=dict)
    intervention_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LedgerShieldAction(Action):
    """Agent action consisting of an action type and payload.

    Attributes:
        action_type: Which tool/intervention/decision to invoke.
        payload: Tool-specific parameters.
    """
    action_type: ActionType
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerShieldObservation(Observation):
    """Full observation available to the agent at each step.

    Contains everything the agent can see: documents, artifacts,
    budget status, risk signals, and the last tool result.

    Attributes:
        case_id: Current case identifier.
        task_type: Task family (task_a through task_e).
        instruction: Natural language task instruction.
        visible_documents: Catalog of visible document metadata.
        revealed_artifacts: List of investigation artifacts.
        pending_events: Async events waiting to resolve.
        budget_remaining: Remaining investigation budget.
        budget_total: Total budget for the episode.
        step_count: Current step number.
        max_steps: Maximum allowed steps.
        case_clock: Logical clock for the case.
        risk_snapshot: Current risk signal summary.
        investigation_status: Investigation progress metrics.
        last_tool_result: Result from the most recent action.
        messages: System messages for the agent.
        allowed_actions: List of valid action types.
        available_interventions: List of intervention action types.
        case_metadata: Additional case context (due date, labels).
        portfolio_context: Cross-case portfolio information.
        sprt_state: Public ASHTG SPRT state for the active case.
        tool_rankings: VoI ranking over currently available tools.
        reward_machine: Reward-machine progress snapshot.
        institutional_memory: Public persistent portfolio memory and loss state.
    """
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
    sprt_state: dict[str, Any] = field(default_factory=dict)
    tool_rankings: dict[str, Any] = field(default_factory=dict)
    reward_machine: dict[str, Any] = field(default_factory=dict)
    institutional_memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerShieldState(State):
    """Internal episode state (not directly visible to agent).

    Tracks everything the environment needs to manage the episode,
    including hidden risk signals, trajectory, and scoring metadata.

    Attributes:
        episode_id: Unique ID for this episode.
        case_id: The loaded case ID.
        task_type: Task family.
        budget_total: Total investigation budget.
        budget_remaining: Remaining budget.
        max_steps: Maximum allowed steps.
        step_count: Current step number.
        case_clock: Logical case clock.
        submitted: Whether a decision has been submitted.
        final_score: Final graded score (set at submission).
        unsafe_outcome: Whether the outcome was unsafe.
        visible_doc_ids: IDs of documents the agent can see.
        revealed_artifact_ids: IDs of revealed investigation artifacts.
        tool_trace: Full trace of all tool calls and results.
        trajectory: Simplified trajectory for grading.
        interventions_taken: List of intervention records.
        observed_risk_signals: Risk signals the agent has discovered.
        hidden_risk_signals: All risk signals (including undiscovered).
        final_outcome: Simulated outcome dict (set at submission).
        handoff_packet: Agent's handoff data for human review.
        pending_event_ids: IDs of pending async events.
        portfolio_metrics: Cross-case portfolio metrics.
        decision_readiness: Computed readiness score (0–1).
        difficulty: Case difficulty level.
        terminal_reason: Why the episode ended.
        pressure_events_seen: IDs of pressure events encountered.
        pressure_resistance_score: Score for resisting adversarial pressure.
        contrastive_pair_id: ID linking contrastive pair cases.
        sprt_state: Serialized SPRT state for sequential hypothesis testing.
        tool_rankings: Latest VoI ranking over available tools.
        reward_machine_state: Serialized reward-machine state.
        calibration_running_average: Running calibration proxy across the episode.
        institutional_metrics: Persistent portfolio metrics after this episode.
        decision_certificate_report: Verifier report for the submitted decision
            certificate.
    """
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
    hidden_risk_signals: list[str] = field(default_factory=list)
    final_outcome: dict[str, Any] = field(default_factory=dict)
    handoff_packet: dict[str, Any] = field(default_factory=dict)
    pending_event_ids: list[str] = field(default_factory=list)
    portfolio_metrics: dict[str, Any] = field(default_factory=dict)
    decision_readiness: float = 0.0
    difficulty: str = "medium"
    terminal_reason: str = ""
    pressure_events_seen: list[str] = field(default_factory=list)
    pressure_resistance_score: float = 0.0
    contrastive_pair_id: str = ""
    sprt_state: dict[str, Any] = field(default_factory=dict)
    tool_rankings: dict[str, Any] = field(default_factory=dict)
    reward_machine_state: dict[str, Any] = field(default_factory=dict)
    calibration_running_average: float = 0.0
    institutional_metrics: dict[str, Any] = field(default_factory=dict)
    decision_certificate_report: dict[str, Any] = field(default_factory=dict)
