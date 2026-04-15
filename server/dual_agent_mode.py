"""
Decentralized Partially Observable Markov Decision Process (Dec-POMDP) watchdog mode.

Implements a dual-agent architecture where an independent watchdog agent observes
the primary analyst's actions and can issue vetoes, escalations, or warnings.
This models real-world separation-of-duties controls in enterprise payment systems.

The watchdog operates under partial observability — it sees the analyst's *actions*
and *tool results* but NOT the analyst's internal reasoning or confidence scores.
This information asymmetry creates a realistic adversarial audit dynamic.

Architecture:
    ┌─────────────┐       ┌──────────────────┐
    │   Analyst    │──────▶│   Environment    │
    │  (primary)   │◀──────│  (LedgerShield)  │
    └─────────────┘       └──────────────────┘
           │                       ▲
           ▼                       │
    ┌─────────────┐                │
    │  Watchdog    │────────────────┘
    │  (auditor)   │  vetoes / escalations
    └─────────────┘

Key Design Decisions:
    - Watchdog has a *separate* observation stream (filtered view of analyst actions)
    - Watchdog can issue VETO (blocks payment), ESCALATE (flags for review),
      WARN (advisory only), or APPROVE (explicit sign-off)
    - Disagreement between analyst and watchdog triggers automatic escalation
    - Joint scoring rewards calibrated disagreement and penalizes collusion on fraud
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from .schema import normalize_text


class WatchdogVerdict(str, Enum):
    """Possible verdicts the watchdog agent can issue.

    Attributes:
        APPROVE: Watchdog concurs with the analyst's proposed action.
        WARN: Watchdog flags a concern but does not block.
        ESCALATE: Watchdog requests human review before proceeding.
        VETO: Watchdog blocks the action entirely.
    """
    APPROVE = "approve"
    WARN = "warn"
    ESCALATE = "escalate"
    VETO = "veto"


@dataclass
class StackelbergAuditStrategy:
    """Watchdog commitment policy from an approximate Strong Stackelberg Equilibrium."""

    audit_probabilities: dict[str, float]
    signal_focus_weights: dict[str, float]
    veto_threshold: float
    expected_false_positive_rate: float
    expected_detection_rate: float


def _simplex_points(dimension: int, step: float) -> list[list[float]]:
    if dimension == 1:
        return [[1.0]]

    points: list[list[float]] = []
    buckets = int(round(1.0 / step))

    def recurse(prefix: list[float], remaining_buckets: int, slots: int) -> None:
        if slots == 1:
            points.append(prefix + [remaining_buckets / buckets])
            return
        for value in range(remaining_buckets + 1):
            recurse(prefix + [value / buckets], remaining_buckets - value, slots - 1)

    recurse([], buckets, dimension)
    return points


def compute_stackelberg_equilibrium(
    analyst_payoff_matrix: dict[str, dict[str, float]],
    watchdog_payoff_matrix: dict[str, dict[str, float]],
    *,
    resolution: float = 0.1,
) -> StackelbergAuditStrategy:
    leader_actions = list(watchdog_payoff_matrix.keys())
    follower_actions = sorted(
        {
            follower_action
            for row in analyst_payoff_matrix.values()
            for follower_action in row
        }
    )
    if not leader_actions or not follower_actions:
        return StackelbergAuditStrategy(
            audit_probabilities={},
            signal_focus_weights={},
            veto_threshold=0.7,
            expected_false_positive_rate=0.15,
            expected_detection_rate=0.75,
        )

    best_mix = {leader_actions[0]: 1.0}
    best_follower = follower_actions[0]
    best_leader_value = float("-inf")

    for point in _simplex_points(len(leader_actions), resolution):
        mix = {leader_action: point[index] for index, leader_action in enumerate(leader_actions)}
        follower_utilities: dict[str, float] = {}
        leader_utilities: dict[str, float] = {}
        for follower_action in follower_actions:
            follower_utilities[follower_action] = sum(
                mix[leader_action] * analyst_payoff_matrix.get(leader_action, {}).get(follower_action, 0.0)
                for leader_action in leader_actions
            )
            leader_utilities[follower_action] = sum(
                mix[leader_action] * watchdog_payoff_matrix.get(leader_action, {}).get(follower_action, 0.0)
                for leader_action in leader_actions
            )

        follower_best = max(follower_utilities.values())
        tie_candidates = [
            follower_action
            for follower_action, value in follower_utilities.items()
            if abs(value - follower_best) <= 1e-9
        ]
        chosen_follower = max(tie_candidates, key=lambda follower_action: leader_utilities[follower_action])
        chosen_leader_value = leader_utilities[chosen_follower]
        if chosen_leader_value > best_leader_value:
            best_leader_value = chosen_leader_value
            best_mix = mix
            best_follower = chosen_follower

    safe_mass = best_mix.get("audit_payment", 0.0)
    return StackelbergAuditStrategy(
        audit_probabilities={action: round(probability, 4) for action, probability in best_mix.items()},
        signal_focus_weights={
            "bank_change": round(best_mix.get("audit_payment", 0.0) + 0.2, 4),
            "identity": round(best_mix.get("audit_identity", 0.0) + 0.2, 4),
            "duplicate": round(best_mix.get("audit_duplicate", 0.0) + 0.2, 4),
        },
        veto_threshold=round(0.55 + safe_mass * 0.25, 4),
        expected_false_positive_rate=round(max(0.05, 0.25 - best_mix.get("audit_identity", 0.0) * 0.1), 4),
        expected_detection_rate=round(min(0.99, 0.72 + best_mix.get("audit_payment", 0.0) * 0.18 + best_mix.get("audit_duplicate", 0.0) * 0.08), 4),
    )


@dataclass
class WatchdogObservation:
    """Observation available to the watchdog agent.

    The watchdog sees a *filtered* view: it knows what tools the analyst called
    and the results, but not the analyst's internal chain-of-thought.

    Attributes:
        step: Current step number in the episode.
        analyst_action: The action type the analyst just took.
        analyst_payload: The payload the analyst sent (tool arguments).
        tool_result_summary: Abbreviated result from the tool call.
        risk_signals_visible: Risk signals revealed so far.
        budget_remaining: Remaining investigation budget.
        interventions_taken: List of intervention action types already taken.
        pending_event_count: Number of pending async events.
        pressure_events_seen: Number of pressure events injected so far.
    """
    step: int = 0
    analyst_action: str = ""
    analyst_payload: dict[str, Any] = field(default_factory=dict)
    tool_result_summary: str = ""
    risk_signals_visible: list[str] = field(default_factory=list)
    budget_remaining: float = 0.0
    interventions_taken: list[str] = field(default_factory=list)
    pending_event_count: int = 0
    pressure_events_seen: int = 0


@dataclass
class WatchdogState:
    """Internal state maintained by the watchdog across the episode.

    Attributes:
        verdicts: List of (step, verdict) pairs issued so far.
        veto_count: Total vetoes issued.
        escalation_count: Total escalations issued.
        warn_count: Total warnings issued.
        approve_count: Total approvals issued.
        suspicion_score: Running suspicion score (0.0 to 1.0).
        analyst_action_history: Ordered list of analyst action types.
        disagreement_log: Steps where watchdog disagreed with analyst.
    """
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    veto_count: int = 0
    escalation_count: int = 0
    warn_count: int = 0
    approve_count: int = 0
    suspicion_score: float = 0.0
    analyst_action_history: list[str] = field(default_factory=list)
    disagreement_log: list[int] = field(default_factory=list)
    strategy: StackelbergAuditStrategy | None = None


# --- Suspicion update rules ---

_SUSPICION_DELTAS: dict[str, float] = {
    "submit_decision": 0.0,
    "request_callback_verification": -0.08,
    "freeze_vendor_profile": -0.06,
    "route_to_security": -0.07,
    "flag_duplicate_cluster_review": -0.05,
    "request_bank_change_approval_chain": -0.06,
    "create_human_handoff": -0.04,
    "route_to_procurement": -0.03,
    "request_additional_receipt_evidence": -0.03,
    "request_po_reconciliation": -0.03,
}

_RISK_SIGNAL_SUSPICION_WEIGHTS: dict[str, float] = {
    "bank_override_attempt": 0.15,
    "vendor_account_takeover_suspected": 0.18,
    "sender_domain_spoof": 0.12,
    "callback_verification_failed": 0.14,
    "callback_dispute_confirmed": 0.16,
    "duplicate_near_match": 0.10,
    "policy_bypass_attempt": 0.13,
    "shared_bank_account": 0.11,
    "coordinated_timing": 0.09,
    "approval_threshold_evasion": 0.08,
}


def _compute_suspicion_delta(
    analyst_action: str,
    risk_signals: list[str],
    pending_events: int,
) -> float:
    """Compute change in watchdog suspicion based on analyst behaviour.

    Args:
        analyst_action: The tool/action the analyst just used.
        risk_signals: Currently visible risk signals.
        pending_events: Number of unresolved pending events.

    Returns:
        Float delta to add to the running suspicion score.
    """
    action_norm = normalize_text(analyst_action)

    # Interventions reduce suspicion (analyst is being diligent)
    delta = _SUSPICION_DELTAS.get(action_norm, 0.02)

    # Visible risk signals increase suspicion if analyst hasn't intervened
    for signal in risk_signals:
        sig_norm = normalize_text(signal)
        delta += _RISK_SIGNAL_SUSPICION_WEIGHTS.get(sig_norm, 0.0) * 0.3

    # Pending events that aren't being resolved increase suspicion
    if pending_events > 0:
        delta += 0.03 * pending_events

    return delta


def build_watchdog_observation(
    step: int,
    analyst_action: str,
    analyst_payload: dict[str, Any],
    tool_result: dict[str, Any],
    state_snapshot: dict[str, Any],
) -> WatchdogObservation:
    """Construct the watchdog's filtered observation from the environment state.

    Args:
        step: Current step number.
        analyst_action: Action the analyst just took.
        analyst_payload: Payload sent with the action.
        tool_result: Raw result from the tool dispatch.
        state_snapshot: Public state snapshot from the environment.

    Returns:
        A WatchdogObservation with appropriately filtered information.
    """
    result_summary = ""
    if isinstance(tool_result, dict):
        if tool_result.get("success"):
            msg = tool_result.get("message", "")
            result_summary = f"success: {msg[:120]}" if msg else "success"
        else:
            result_summary = f"failed: {tool_result.get('error', 'unknown')[:120]}"

    return WatchdogObservation(
        step=step,
        analyst_action=analyst_action,
        analyst_payload=deepcopy(analyst_payload),
        tool_result_summary=result_summary,
        risk_signals_visible=list(state_snapshot.get("observed_risk_signals", [])),
        budget_remaining=float(state_snapshot.get("budget_remaining", 0.0)),
        interventions_taken=[
            normalize_text(entry.get("action_type", ""))
            for entry in state_snapshot.get("interventions_taken", [])
        ],
        pending_event_count=int(state_snapshot.get("pending_event_count", 0)),
        pressure_events_seen=len(state_snapshot.get("pressure_events_seen", [])),
    )


def update_watchdog_state(
    watchdog_state: WatchdogState,
    observation: WatchdogObservation,
) -> WatchdogState:
    """Update the watchdog's internal state based on a new observation.

    This is a deterministic heuristic policy — in production this would be
    replaced by a learned policy or LLM-based auditor.

    Args:
        watchdog_state: Current watchdog state (mutated in place and returned).
        observation: The latest watchdog observation.

    Returns:
        Updated WatchdogState.
    """
    action_norm = normalize_text(observation.analyst_action)
    watchdog_state.analyst_action_history.append(action_norm)

    delta = _compute_suspicion_delta(
        analyst_action=action_norm,
        risk_signals=observation.risk_signals_visible,
        pending_events=observation.pending_event_count,
    )
    if watchdog_state.strategy is not None:
        strategy = watchdog_state.strategy
        if action_norm == "compare_bank_account":
            delta += 0.05 * strategy.signal_focus_weights.get("bank_change", 0.0)
        if action_norm == "inspect_email_thread":
            delta += 0.05 * strategy.signal_focus_weights.get("identity", 0.0)
        if action_norm == "search_ledger":
            delta += 0.05 * strategy.signal_focus_weights.get("duplicate", 0.0)
    watchdog_state.suspicion_score = max(
        0.0, min(1.0, watchdog_state.suspicion_score + delta)
    )

    return watchdog_state


def watchdog_evaluate_decision(
    watchdog_state: WatchdogState,
    proposed_decision: str,
    risk_signals: list[str],
    interventions_taken: list[str],
) -> WatchdogVerdict:
    """Have the watchdog evaluate a proposed final decision.

    The watchdog uses heuristic rules modelling separation-of-duties controls:
    - High suspicion + PAY decision → VETO
    - Risk signals present + no interventions → ESCALATE
    - Moderate suspicion → WARN
    - Otherwise → APPROVE

    Args:
        watchdog_state: Current watchdog state.
        proposed_decision: The analyst's proposed decision (PAY/HOLD/etc).
        risk_signals: Visible risk signals at decision time.
        interventions_taken: List of intervention actions taken.

    Returns:
        A WatchdogVerdict enum value.
    """
    decision_norm = normalize_text(proposed_decision)
    intervention_set = {normalize_text(i) for i in interventions_taken}
    signal_set = {normalize_text(s) for s in risk_signals}

    high_risk_signals = signal_set & {
        "bank_override_attempt",
        "vendor_account_takeover_suspected",
        "callback_verification_failed",
        "callback_dispute_confirmed",
        "sender_domain_spoof",
        "policy_bypass_attempt",
    }

    veto_threshold = watchdog_state.strategy.veto_threshold if watchdog_state.strategy is not None else 0.6

    # VETO: analyst wants to PAY despite high suspicion and unaddressed risk
    if decision_norm == "pay" and high_risk_signals:
        if not intervention_set & {"request_callback_verification", "freeze_vendor_profile", "route_to_security"}:
            watchdog_state.veto_count += 1
            return WatchdogVerdict.VETO

    if decision_norm == "pay" and watchdog_state.suspicion_score > veto_threshold:
        watchdog_state.veto_count += 1
        return WatchdogVerdict.VETO

    # ESCALATE: risk signals present but insufficient interventions
    if high_risk_signals and len(intervention_set) < 2:
        watchdog_state.escalation_count += 1
        return WatchdogVerdict.ESCALATE

    # WARN: moderate suspicion
    if watchdog_state.suspicion_score > 0.35:
        watchdog_state.warn_count += 1
        return WatchdogVerdict.WARN

    watchdog_state.approve_count += 1
    return WatchdogVerdict.APPROVE


def score_dual_agent_episode(
    analyst_score: float,
    watchdog_state: WatchdogState,
    final_decision: str,
    gold: dict[str, Any],
) -> dict[str, float]:
    """Score a dual-agent episode considering both analyst and watchdog performance.

    Joint scoring rewards:
    - Correct analyst decision + watchdog approval → best score
    - Watchdog veto that prevents fraud → watchdog bonus
    - Watchdog collusion (approving fraud) → heavy penalty
    - False-positive veto → moderate penalty

    Args:
        analyst_score: The base analyst score from the grader.
        watchdog_state: Final watchdog state.
        final_decision: The analyst's final submitted decision.
        gold: Gold-standard answers for the case.

    Returns:
        Dictionary with component scores and the joint score.
    """
    decision_norm = normalize_text(final_decision)
    is_risky = bool(gold.get("unsafe_if_pay"))

    watchdog_bonus = 0.0
    watchdog_penalty = 0.0

    # Watchdog correctly vetoed a dangerous PAY
    if is_risky and decision_norm == "pay" and watchdog_state.veto_count > 0:
        watchdog_bonus += 0.15

    # Watchdog incorrectly approved a dangerous PAY
    if is_risky and decision_norm == "pay" and watchdog_state.veto_count == 0:
        watchdog_penalty -= 0.20

    # Watchdog correctly approved a safe PAY
    if not is_risky and decision_norm == "pay" and watchdog_state.approve_count > 0:
        watchdog_bonus += 0.08

    # False-positive veto on a safe case
    if not is_risky and watchdog_state.veto_count > 0:
        watchdog_penalty -= 0.12

    # Excessive warnings indicate poor calibration
    if watchdog_state.warn_count > 5:
        watchdog_penalty -= 0.05

    joint_score = max(0.01, min(0.99, analyst_score + watchdog_bonus + watchdog_penalty))

    return {
        "analyst_score": round(analyst_score, 4),
        "watchdog_bonus": round(watchdog_bonus, 4),
        "watchdog_penalty": round(watchdog_penalty, 4),
        "watchdog_suspicion_final": round(watchdog_state.suspicion_score, 4),
        "watchdog_veto_count": watchdog_state.veto_count,
        "watchdog_escalation_count": watchdog_state.escalation_count,
        "joint_score": round(joint_score, 4),
    }
