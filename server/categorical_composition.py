from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MDPComponent:
    state_space: set[str]
    action_space: set[str]
    required_observations: set[str]
    reward_function: Callable[[dict[str, Any]], float]
    temporal_spec: str
    name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def compose_tasks(base: MDPComponent, extension: MDPComponent) -> MDPComponent:
    def composed_reward(context: dict[str, Any]) -> float:
        return float(base.reward_function(context)) + float(extension.reward_function(context))

    return MDPComponent(
        name=f"{base.name}+{extension.name}".strip("+"),
        state_space=set(base.state_space) | set(extension.state_space),
        action_space=set(base.action_space) | set(extension.action_space),
        required_observations=set(base.required_observations) | set(extension.required_observations),
        reward_function=composed_reward,
        temporal_spec=f"({base.temporal_spec}) and ({extension.temporal_spec})",
        metadata={**base.metadata, **extension.metadata},
    )


def _constant_reward(_: dict[str, Any]) -> float:
    return 0.0


BASE_INVESTIGATION = MDPComponent(
    name="BaseInvestigation",
    state_space={"case", "budget", "signals"},
    action_space={"ocr", "zoom", "lookup_policy"},
    required_observations={"documents", "risk_snapshot"},
    reward_function=_constant_reward,
    temporal_spec="F submit_decision",
)

DOCUMENT_EXTRACTION = MDPComponent(
    name="DocumentExtraction",
    state_space={"invoice_fields", "evidence"},
    action_space={"ocr", "zoom"},
    required_observations={"visible_documents"},
    reward_function=_constant_reward,
    temporal_spec="F ocr",
)

THREE_WAY_MATCH = MDPComponent(
    name="ThreeWayMatch",
    state_space={"po_state", "receipt_state"},
    action_space={"lookup_po", "lookup_receipt"},
    required_observations={"policy_rules"},
    reward_function=_constant_reward,
    temporal_spec="F lookup_po and F lookup_receipt",
)

DUPLICATE_DETECTION = MDPComponent(
    name="DuplicateDetection",
    state_space={"duplicate_cluster"},
    action_space={"search_ledger", "flag_duplicate_cluster_review"},
    required_observations={"ledger_hits"},
    reward_function=_constant_reward,
    temporal_spec="F search_ledger",
)

IDENTITY_VERIFICATION = MDPComponent(
    name="IdentityVerification",
    state_space={"sender_authenticity", "bank_alignment"},
    action_space={"inspect_email_thread", "compare_bank_account", "request_callback_verification"},
    required_observations={"email_thread"},
    reward_function=_constant_reward,
    temporal_spec="F inspect_email_thread and F compare_bank_account",
)

CAMPAIGN_DETECTION = MDPComponent(
    name="CampaignDetection",
    state_space={"portfolio_linkage"},
    action_space={"search_ledger", "route_to_security", "freeze_vendor_profile"},
    required_observations={"portfolio_context"},
    reward_function=_constant_reward,
    temporal_spec="F route_to_security",
)


def task_family_component(task_type: str) -> MDPComponent:
    task_type = str(task_type)
    if task_type == "task_a":
        return compose_tasks(BASE_INVESTIGATION, DOCUMENT_EXTRACTION)
    if task_type == "task_b":
        return compose_tasks(task_family_component("task_a"), THREE_WAY_MATCH)
    if task_type == "task_c":
        return compose_tasks(task_family_component("task_b"), DUPLICATE_DETECTION)
    if task_type == "task_d":
        return compose_tasks(task_family_component("task_c"), IDENTITY_VERIFICATION)
    if task_type == "task_e":
        return compose_tasks(task_family_component("task_d"), CAMPAIGN_DETECTION)
    return BASE_INVESTIGATION
