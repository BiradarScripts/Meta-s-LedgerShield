"""
LedgerShield OpenEnv Environment.

Implements a POMDP-style environment for evaluating AI agents on
enterprise accounts-payable (AP) payment integrity tasks. The agent
must investigate invoices, gather evidence, take interventions, and
submit a final payment decision.

Environment Loop:
    1. ``reset()`` loads a case and returns the initial observation.
    2. ``step(action)`` processes one action (tool call, intervention,
       or final decision) and returns the next observation.
    3. The episode ends when the agent submits a decision, exhausts its
       budget, or exceeds the maximum step count.

Reward Design:
    - Potential-Based Reward Shaping (PBRS) with configurable scale.
    - Information-gain bonus for discovering novel risk signals.
    - Milestone rewards for completing key investigation steps.
    - Terminal reward from the grading rubric.

Gymnasium Compatibility:
    - ``truncated`` vs ``terminated`` distinction (3.2).
    - ``render()`` method for text-based episode summaries (3.3).
    - ``action_space()`` / ``observation_space()`` class methods (3.4).
"""

from __future__ import annotations

import math
from dataclasses import asdict
import random
import uuid
from typing import Any

from models import LedgerShieldObservation, LedgerShieldReward, LedgerShieldState
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
    advance_pending_events,
    build_hidden_world,
    decision_readiness,
    inject_pressure_event,
    investigation_status,
    pending_events_public,
    pressure_resistance_score,
    public_state_snapshot,
    public_revealed_artifacts,
    risk_snapshot,
    state_potential,
    system_state_snapshot,
)

# ── Tool cost table ──────────────────────────────────────────────────────────
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

# ── Reward shaping constants (Phase 3.1) ─────────────────────────────────────
SHAPING_GAMMA = 0.98
SHAPING_SCALE = 0.35  # Upgraded from 0.18 → 0.35

# ── Information-gain bonus (Phase 5.3) ───────────────────────────────────────
INFO_GAIN_BONUS = 0.08

# ── Milestone reward definitions ─────────────────────────────────────────────
MILESTONE_REWARDS: dict[str, float] = {
    "first_risk_signal": 0.05,
    "callback_requested": 0.04,
    "all_required_actions": 0.06,
    "artifact_revealed": 0.03,
}

# ── Degenerate evidence cap (Phase 4.5) ──────────────────────────────────────
DEGENERATE_EVIDENCE_CAP = 0.25

# ── Formalized score constants ───────────────────────────────────────────────
INTERVENTION_BASE_SCORE = 0.15  # Tightened from 0.35 (Phase 2.3)


class LedgerShieldEnvironment(Environment):
    """POMDP environment for enterprise payment integrity evaluation.

    This environment simulates a realistic accounts-payable investigation
    workflow where an AI agent must analyze invoices, verify vendor
    identities, check policies, and make payment decisions.

    The agent operates under partial observability: it cannot see hidden
    risk signals directly but must discover them through tool usage and
    interventions.

    Attributes:
        db: Pre-loaded database of cases, vendors, policies, etc.
        rng: Seeded random number generator.
        current_case: The currently loaded case dictionary.
    """

    def __init__(self, db: dict[str, Any] | None = None) -> None:
        """Initialize the LedgerShield environment.

        Args:
            db: Optional pre-loaded database dict. If None, loads from
                fixture files via ``load_all()``.
        """
        super().__init__()
        self.db = db if db is not None else load_all()
        self.rng = random.Random(42)
        self.current_case: dict[str, Any] | None = None
        self._state = LedgerShieldState()
        self._last_reward = 0.0
        self._last_done = False
        self._last_truncated = False
        self._last_terminated = False
        self._last_info: dict[str, Any] = {}
        self._hidden_world: dict[str, Any] = {}
        self._milestones_awarded: set[str] = set()
        self._render_mode: str | None = None

    # ── Gymnasium-compatible space definitions (Phase 3.4) ───────────────

    @classmethod
    def action_space(cls) -> dict[str, Any]:
        """Return a formal description of the action space.

        The action space is a dictionary with:
        - ``type``: ``"Dict"`` (composite action).
        - ``action_type``: ``"Discrete"`` over allowed action strings.
        - ``payload``: ``"Dict"`` with tool-specific parameters.

        Returns:
            Dictionary describing the action space structure.
        """
        return {
            "type": "Dict",
            "spaces": {
                "action_type": {
                    "type": "Discrete",
                    "n": len(ALLOWED_ACTIONS),
                    "values": list(ALLOWED_ACTIONS),
                },
                "payload": {
                    "type": "Dict",
                    "description": "Tool-specific parameters (varies by action_type)",
                    "examples": {
                        "zoom": {"doc_id": "str", "page": "int", "region": "[x1,y1,x2,y2]"},
                        "ocr": {"doc_id": "str", "mode": "'fast'|'accurate'"},
                        "lookup_vendor": {"vendor_key": "str"},
                        "submit_decision": {
                            "decision": "PAY|HOLD|NEEDS_REVIEW|ESCALATE_FRAUD",
                            "confidence": "float(0-1)",
                            "reason_codes": "list[str]",
                        },
                    },
                },
            },
        }

    @classmethod
    def observation_space(cls) -> dict[str, Any]:
        """Return a formal description of the observation space.

        Returns:
            Dictionary describing the observation space structure.
        """
        return {
            "type": "Dict",
            "spaces": {
                "case_id": {"type": "Text"},
                "task_type": {"type": "Discrete", "values": ["task_a", "task_b", "task_c", "task_d", "task_e"]},
                "instruction": {"type": "Text"},
                "visible_documents": {"type": "Sequence", "element": "DocumentCatalogEntry"},
                "revealed_artifacts": {"type": "Sequence", "element": "ArtifactEntry"},
                "pending_events": {"type": "Sequence", "element": "PendingEvent"},
                "budget_remaining": {"type": "Box", "low": 0.0, "high": 30.0},
                "budget_total": {"type": "Box", "low": 0.0, "high": 30.0},
                "step_count": {"type": "Discrete", "low": 0, "high": 50},
                "max_steps": {"type": "Discrete", "low": 1, "high": 50},
                "case_clock": {"type": "Discrete", "low": 0, "high": 50},
                "risk_snapshot": {"type": "Dict"},
                "investigation_status": {"type": "Dict"},
                "last_tool_result": {"type": "Dict"},
                "messages": {"type": "Sequence", "element": "Text"},
                "allowed_actions": {"type": "Sequence", "element": "Text"},
                "available_interventions": {"type": "Sequence", "element": "Text"},
                "case_metadata": {"type": "Dict"},
                "portfolio_context": {"type": "Dict"},
            },
        }

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def state(self) -> LedgerShieldState:
        """Return the current internal state."""
        return self._state

    def public_state(self) -> dict[str, Any]:
        """Return the public (non-hidden) state snapshot."""
        return public_state_snapshot(self._state, self._hidden_world)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _select_case(self, seed: int | None = None, case_id: str | None = None) -> dict[str, Any]:
        """Select a case by ID or random sampling.

        Args:
            seed: Random seed for case selection.
            case_id: Specific case ID to load.

        Returns:
            Case dictionary.

        Raises:
            ValueError: If case_id is provided but not found.
        """
        if case_id:
            case = self.db["cases_by_id"].get(case_id)
            if case is None:
                raise ValueError(f"unknown case_id: {case_id}")
            return case
        rng = random.Random(seed) if seed is not None else self.rng
        return rng.choice(self.db["cases"])

    def _initial_visible_doc_ids(self) -> list[str]:
        """Return initial visible document IDs for the current case."""
        assert self.current_case is not None
        doc_ids = self.current_case.get("initial_visible_doc_ids") or [
            doc.get("doc_id")
            for doc in self.current_case.get("documents", [])
            if doc.get("doc_id")
        ]
        return [str(doc_id) for doc_id in doc_ids]

    def _all_documents(self) -> list[dict[str, Any]]:
        """Return all documents (static + dynamic) for the current case."""
        assert self.current_case is not None
        docs = list(self.current_case.get("documents", []))
        dynamic_docs = self._hidden_world.get("dynamic_documents", {}) or {}
        docs.extend(dynamic_docs.values())
        return docs

    def _visible_document_catalog(self) -> list[dict[str, Any]]:
        """Build the visible document catalog for the current observation."""
        assert self.current_case is not None
        docs: list[dict[str, Any]] = []
        visible_set = set(self._state.visible_doc_ids)

        for doc in self._all_documents():
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
                        "thumbnail", "zoom", "get_doc_crop",
                        "ocr_fast", "ocr_accurate",
                    ],
                }
            )
        return docs

    def _observation(
        self,
        tool_result: dict[str, Any] | None = None,
        messages: list[str] | None = None,
    ) -> LedgerShieldObservation:
        """Construct an observation from the current state.

        Args:
            tool_result: Result of the last tool call (if any).
            messages: List of messages to include in the observation.

        Returns:
            LedgerShieldObservation dataclass.
        """
        assert self.current_case is not None
        return LedgerShieldObservation(
            case_id=self._state.case_id,
            task_type=self._state.task_type,
            instruction=self.current_case["instruction"],
            visible_documents=self._visible_document_catalog(),
            revealed_artifacts=public_revealed_artifacts(self._state, self._hidden_world),
            pending_events=pending_events_public(self._hidden_world),
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
                "task_label": self.current_case.get("task_label", ""),
                "due_date_days": int(self.current_case.get("due_date_days", 14) or 14),
            },
            portfolio_context=dict(self._hidden_world.get("campaign_context", {})),
        )

    def _reward_payload(
        self,
        *,
        value: float,
        terminal: bool,
        components: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a structured reward payload.

        Args:
            value: Scalar reward value.
            terminal: Whether this is the terminal reward.
            components: Breakdown of reward components.
            metadata: Additional reward metadata.

        Returns:
            Serialized LedgerShieldReward dict.
        """
        return LedgerShieldReward(
            value=round(float(value), 4),
            terminal=terminal,
            components={key: round(float(val), 4) for key, val in (components or {}).items()},
            metadata=metadata or {},
        ).model_dump()

    # ── Milestone tracking (Phase 3.1) ───────────────────────────────────

    def _check_milestones(self) -> float:
        """Check and award milestone rewards.

        Returns:
            Total milestone reward for this step.
        """
        bonus = 0.0

        # First risk signal discovery
        if (self._state.observed_risk_signals
                and "first_risk_signal" not in self._milestones_awarded):
            self._milestones_awarded.add("first_risk_signal")
            bonus += MILESTONE_REWARDS["first_risk_signal"]

        # Callback requested
        callback_taken = any(
            step.get("action_type") == "request_callback_verification"
            for step in self._state.trajectory
        )
        if callback_taken and "callback_requested" not in self._milestones_awarded:
            self._milestones_awarded.add("callback_requested")
            bonus += MILESTONE_REWARDS["callback_requested"]

        # Artifact revealed
        if (self._state.revealed_artifact_ids
                and "artifact_revealed" not in self._milestones_awarded):
            self._milestones_awarded.add("artifact_revealed")
            bonus += MILESTONE_REWARDS["artifact_revealed"]

        # All required actions completed
        required = set(self._hidden_world.get("required_actions", []))
        successful = {
            step.get("action_type", "")
            for step in self._state.trajectory
            if step.get("success", True)
        }
        if required and required <= successful and "all_required_actions" not in self._milestones_awarded:
            self._milestones_awarded.add("all_required_actions")
            bonus += MILESTONE_REWARDS["all_required_actions"]

        return bonus

    # ── Information-theoretic exploration bonus (Phase 5.3) ───────────────

    def _info_gain_bonus(self, signals_before: int, signals_after: int) -> float:
        """Calculate information-gain bonus for discovering new risk signals.

        Uses an entropy-inspired formula: bonus scales with the log-ratio
        of information gained, saturating at INFO_GAIN_BONUS.

        Args:
            signals_before: Number of observed risk signals before action.
            signals_after: Number of observed risk signals after action.

        Returns:
            Float bonus value.
        """
        new_signals = max(0, signals_after - signals_before)
        if new_signals == 0:
            return 0.0

        total_hidden = max(len(self._hidden_world.get("hidden_risk_signals", [])), 1)
        coverage_before = signals_before / total_hidden
        coverage_after = signals_after / total_hidden

        # Log-ratio information gain (bounded)
        if coverage_before >= 1.0:
            return 0.0
        gain = math.log2(max(1.0 - coverage_before, 0.01)) - math.log2(max(1.0 - coverage_after, 0.01))
        return min(INFO_GAIN_BONUS, gain * 0.04)

    # ── Core API ─────────────────────────────────────────────────────────

    def reset(self, seed: int | None = None, case_id: str | None = None) -> LedgerShieldObservation:
        """Reset the environment and load a new case.

        Args:
            seed: Optional seed for case selection.
            case_id: Optional specific case to load.

        Returns:
            Initial observation for the new episode.
        """
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
            portfolio_metrics=dict(self._hidden_world.get("campaign_context", {})),
            contrastive_pair_id=str(self.current_case.get("contrastive_pair_id", "")),
        )

        self._last_reward = 0.0
        self._last_done = False
        self._last_truncated = False
        self._last_terminated = False
        self._last_info = {"case_id": self._state.case_id}
        self._milestones_awarded = set()

        return self._observation(messages=[f"Loaded case {self._state.case_id}"])

    def _apply_cost(self, tool_name: str, payload: dict[str, Any]) -> float:
        """Calculate the budget cost for a tool invocation.

        Args:
            tool_name: Name of the tool being called.
            payload: Tool payload (used for OCR mode selection).

        Returns:
            Float cost value.
        """
        if tool_name == "ocr":
            return TOOL_COSTS["ocr_accurate"] if payload.get("mode", "fast") == "accurate" else TOOL_COSTS["ocr_fast"]
        return TOOL_COSTS.get(tool_name, 0.0)

    def _dispatch_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call to the appropriate handler.

        Args:
            tool_name: Name of the tool to invoke.
            payload: Tool-specific parameters.

        Returns:
            Raw tool result dictionary.
        """
        assert self.current_case is not None
        overrides = self.current_case.get("context_overrides", {}) or {}

        dispatch_map = {
            "zoom": lambda: zoom_tool(self.current_case, payload),
            "get_doc_crop": lambda: get_doc_crop_tool(self.current_case, payload),
            "ocr": lambda: ocr_tool(self.current_case, payload),
            "lookup_vendor": lambda: lookup_vendor_tool(self.db["vendors_by_key"], payload),
            "lookup_vendor_history": lambda: lookup_vendor_history_tool(
                overrides.get("vendor_history", self.db["vendor_history"]), payload),
            "lookup_policy": lambda: lookup_policy_tool(self.db["policy_by_id"], self.db["policy_rules"], payload),
            "lookup_po": lambda: lookup_po_tool(self.db["po_by_id"], payload),
            "lookup_receipt": lambda: lookup_receipt_tool(self.db["receipt_by_id"], payload),
            "search_ledger": lambda: search_ledger_tool(
                overrides.get("ledger_index", self.db["ledger_index"]), payload),
            "inspect_email_thread": lambda: inspect_email_thread_tool(
                self.current_case, self.db["email_threads"], payload),
            "compare_bank_account": lambda: compare_bank_account_tool(self.db["vendors_by_key"], payload),
        }

        handler = dispatch_map.get(tool_name)
        if handler:
            return handler()
        return {"error": f"unknown action_type: {tool_name}"}

    def _handle_intervention(
        self,
        action_type: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Handle an intervention action.

        Args:
            action_type: The intervention action type.
            payload: Intervention parameters.

        Returns:
            Tuple of (result_dict, messages_list).
        """
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
        """Normalize a raw tool result into a standard format.

        Args:
            tool_name: Name of the tool.
            raw: Raw result from tool dispatch.
            cost: Budget cost incurred.

        Returns:
            Tuple of (normalized_result, messages).
        """
        return normalized_result_with_signals(
            state=self._state,
            tool_name=tool_name,
            raw=raw,
            cost=cost,
        )

    def _investigation_summary(self) -> dict[str, Any]:
        """Build a summary of the investigation for grading.

        Returns:
            Dictionary with investigation statistics.
        """
        return {
            "tool_calls": len(self._state.tool_trace),
            "interventions_taken": len(self._state.interventions_taken),
            "revealed_artifact_ids": list(self._state.revealed_artifact_ids),
            "observed_risk_signals": list(self._state.observed_risk_signals),
        }

    def step(self, action: Any) -> LedgerShieldObservation:
        """Process one agent action and return the next observation.

        This is the core environment loop. Each call:
        1. Validates the action.
        2. Dispatches the tool/intervention/decision.
        3. Updates budget, state, and trajectory.
        4. Computes reward (PBRS + info-gain + milestones).
        5. Checks termination conditions.

        Args:
            action: A LedgerShieldAction with action_type and payload.

        Returns:
            The next LedgerShieldObservation.

        Raises:
            RuntimeError: If reset() was not called first.
        """
        if self.current_case is None:
            raise RuntimeError("reset() must be called before step().")

        if self._last_done:
            return self._observation(messages=["Episode already complete."])

        payload = getattr(action, "payload", {}) or {}
        action_type = getattr(action, "action_type", "")

        self._state.step_count += 1
        self._state.case_clock += 1
        potential_before = state_potential(self._state, self._hidden_world)
        signals_before = len(self._state.observed_risk_signals)

        if action_type not in ALLOWED_ACTIONS:
            self._last_reward = -0.05
            self._last_done = False
            self._last_truncated = False
            self._last_terminated = False
            reward_model = self._reward_payload(
                value=-0.05,
                terminal=False,
                components={"failure_penalty": -0.05},
                metadata={"action_type": action_type, "error": "action_not_allowed"},
            )
            self._last_info = {"error": f"Action not allowed: {action_type}", "reward_model": reward_model}
            return self._observation(
                tool_result={
                    "tool_name": action_type,
                    "success": False,
                    "error": f"Action not allowed: {action_type}",
                    "message": f"Action not allowed: {action_type}",
                    "cost": 0.0,
                    "reward_model": reward_model,
                },
                messages=[f"Action not allowed: {action_type}"],
            )

        done = False
        truncated = False
        terminated = False
        reward = 0.0
        info: dict[str, Any] = {}
        reward_components: dict[str, float] = {}
        reward_metadata: dict[str, Any] = {"action_type": action_type}

        if action_type == "submit_decision":
            submitted = dict(payload)
            decision = submitted.get("decision")

            if decision not in ALLOWED_DECISIONS:
                self._last_reward = -0.25
                self._last_done = False
                reward_model = self._reward_payload(
                    value=-0.25,
                    terminal=False,
                    components={"failure_penalty": -0.25},
                    metadata={"action_type": action_type, "error": "invalid_decision"},
                )
                self._last_info = {"error": f"Invalid decision: {decision}", "reward_model": reward_model}
                return self._observation(
                    tool_result={
                        "tool_name": "submit_decision",
                        "success": False,
                        "error": f"Invalid decision: {decision}",
                        "message": f"Invalid decision: {decision}",
                        "cost": 0.0,
                        "reward_model": reward_model,
                    },
                    messages=[f"Invalid decision: {decision}"],
                )

            budget_used = max(self._state.budget_total - self._state.budget_remaining, 0.0)
            budget_penalty = (budget_used / max(self._state.budget_total, 1.0)) * 0.12
            self._state.pressure_resistance_score = round(
                pressure_resistance_score(self._state, self._hidden_world, decision),
                4,
            )

            outcome = simulate_outcome(
                submitted=submitted,
                trajectory=self._state.trajectory,
                hidden_world=self._hidden_world,
                final_state=system_state_snapshot(self._state, self._hidden_world),
            )

            internal_system_state = system_state_snapshot(self._state, self._hidden_world)

            final_score, breakdown = score_submission(
                task_type=self._state.task_type,
                submitted=submitted,
                gold=self.current_case["gold"],
                budget_penalty=budget_penalty,
                trajectory=self._state.trajectory,
                outcome=outcome,
                investigation_summary=self._investigation_summary(),
                final_state=internal_system_state,
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
            self._state.portfolio_metrics = dict(outcome.get("portfolio_metrics", {}))

            public_system_state = public_state_snapshot(self._state, self._hidden_world)

            done = True
            terminated = True  # Phase 3.2: decision submission is a true termination
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
                "system_state": public_system_state,
                "pressure_resistance_score": self._state.pressure_resistance_score,
                "message": "Decision submitted and graded.",
                "cost": 0.0,
            }

            info = {
                "final_score": final_score,
                "score_breakdown": breakdown,
                "unsafe_outcome": self._state.unsafe_outcome,
                "outcome": outcome,
                "system_state": public_system_state,
                "pressure_resistance_score": self._state.pressure_resistance_score,
            }
            reward_components = {"final_score": final_score}
            reward_metadata.update(
                {
                    "unsafe_outcome": self._state.unsafe_outcome,
                    "budget_penalty": round(budget_penalty, 4),
                    "pressure_resistance_score": self._state.pressure_resistance_score,
                }
            )
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

            cost_penalty = -cost * 0.03
            novel_signal_bonus = 0.04 if result.get("novel_signal_count", 0) > 0 else 0.0
            ig_bonus = self._info_gain_bonus(observed_before, observed_after)
            reward = cost_penalty + novel_signal_bonus + ig_bonus
            info = {
                "tool_name": action_type,
                "success": result["success"],
                "intervention": True,
            }
            reward_components = {
                "cost_penalty": cost_penalty,
                "novel_signal_bonus": novel_signal_bonus,
                "info_gain_bonus": round(ig_bonus, 4),
            }
            reward_metadata.update(
                {
                    "intervention": True,
                    "novel_signal_count": int(result.get("novel_signal_count", 0) or 0),
                }
            )

        else:
            raw_result = self._dispatch_tool(action_type, payload)
            cost = self._apply_cost(action_type, payload)
            result, messages = self._normalize_tool_result(action_type, raw_result, cost)

            observed_after = len(self._state.observed_risk_signals)

            cost_penalty = -cost * 0.05
            novel_signal_bonus = 0.0
            failure_penalty = 0.0
            ig_bonus = self._info_gain_bonus(signals_before, observed_after)
            reward = cost_penalty + ig_bonus
            if result.get("novel_signal_count", 0) > 0:
                novel_signal_bonus = min(0.06, 0.02 * result["novel_signal_count"])
                reward += novel_signal_bonus
            if not result["success"]:
                failure_penalty = -0.05
                reward += failure_penalty

            info = {
                "tool_name": action_type,
                "success": result["success"],
            }
            reward_components = {
                "cost_penalty": cost_penalty,
                "novel_signal_bonus": novel_signal_bonus,
                "failure_penalty": failure_penalty,
                "info_gain_bonus": round(ig_bonus, 4),
            }
            reward_metadata.update(
                {
                    "novel_signal_count": int(result.get("novel_signal_count", 0) or 0),
                    "success": bool(result.get("success", False)),
                }
            )

        self._state.budget_remaining = round(max(self._state.budget_remaining - cost, 0.0), 4)

        ready_artifacts, async_messages, async_signals = advance_pending_events(self._state, self._hidden_world)
        if ready_artifacts:
            result["async_artifacts"] = ready_artifacts
            result["revealed_artifact_ids"] = [artifact.get("artifact_id") for artifact in ready_artifacts]
            result["novel_signal_count"] = int(result.get("novel_signal_count", 0) or 0) + async_signals
            messages = list(messages) + async_messages

        injected_doc, pressure_messages = inject_pressure_event(self._state, self._hidden_world)
        if injected_doc:
            result["pressure_event"] = {
                "doc_id": injected_doc.get("doc_id"),
                "doc_type": injected_doc.get("doc_type"),
            }
            messages = list(messages) + pressure_messages

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

        # Phase 3.2: Distinguish truncated vs terminated
        if self._state.step_count >= self._state.max_steps and not done:
            done = True
            truncated = True  # This is a truncation, not a true termination
            self._state.terminal_reason = "max_steps_reached"
            info["truncated"] = True
            messages = list(messages) + ["Maximum steps reached. Episode truncated."]

        if self._state.budget_remaining <= 0 and not done:
            done = True
            truncated = True  # Budget exhaustion is also truncation
            self._state.terminal_reason = "budget_exhausted"
            info["budget_exhausted"] = True
            info["truncated"] = True
            messages = list(messages) + ["Budget exhausted. Episode truncated."]

        # Milestone rewards (Phase 3.1)
        milestone_bonus = self._check_milestones() if not done else 0.0
        reward += milestone_bonus
        if milestone_bonus > 0:
            reward_components["milestone_bonus"] = round(milestone_bonus, 4)

        self._state.decision_readiness = round(decision_readiness(self._state, self._hidden_world), 4)
        potential_after = state_potential(self._state, self._hidden_world)
        shaping_delta = SHAPING_SCALE * ((SHAPING_GAMMA * potential_after) - potential_before)
        reward += shaping_delta
        reward = max(-1.0, min(1.0, reward))
        reward_components["potential_delta"] = round(shaping_delta, 4)

        if done and self._state.terminal_reason:
            reward_metadata["terminal_reason"] = self._state.terminal_reason

        # Phase 3.2: Add truncated/terminated flags to info
        info["truncated"] = truncated
        info["terminated"] = terminated

        reward_model = self._reward_payload(
            value=reward,
            terminal=done,
            components=reward_components,
            metadata=reward_metadata,
        )
        result["reward_model"] = reward_model
        info["reward_model"] = reward_model
        if ready_artifacts:
            info["async_artifacts"] = ready_artifacts

        obs = self._observation(tool_result=result, messages=messages)
        self._last_reward = reward
        self._last_done = done
        self._last_truncated = truncated
        self._last_terminated = terminated
        self._last_info = info
        return obs

    # ── Render (Phase 3.3) ───────────────────────────────────────────────

    def render(self, mode: str = "text") -> str | None:
        """Render the current episode state as a text summary.

        Provides a human-readable summary of the episode for debugging
        and analysis. Includes case info, investigation progress, risk
        signals, and budget status.

        Args:
            mode: Render mode. Currently only 'text' is supported.

        Returns:
            String summary when mode='text', None otherwise.
        """
        if mode != "text":
            return None

        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("LEDGERSHIELD EPISODE SUMMARY")
        lines.append("=" * 60)

        lines.append(f"Episode ID:  {self._state.episode_id}")
        lines.append(f"Case ID:     {self._state.case_id}")
        lines.append(f"Task Type:   {self._state.task_type}")
        lines.append(f"Difficulty:  {self._state.difficulty}")
        lines.append(f"Step:        {self._state.step_count}/{self._state.max_steps}")
        lines.append(f"Budget:      {self._state.budget_remaining:.2f}/{self._state.budget_total:.2f}")
        lines.append(f"Submitted:   {self._state.submitted}")
        lines.append(f"Done:        {self._last_done}")

        if self._last_done:
            lines.append(f"Truncated:   {self._last_truncated}")
            lines.append(f"Terminated:  {self._last_terminated}")
            lines.append(f"Reason:      {self._state.terminal_reason}")

        lines.append("")
        lines.append("── Risk Signals ──")
        observed = self._state.observed_risk_signals
        hidden = self._hidden_world.get("hidden_risk_signals", [])
        lines.append(f"  Hidden:    {len(hidden)}")
        lines.append(f"  Observed:  {len(observed)}")
        for sig in observed:
            lines.append(f"    • {sig}")

        lines.append("")
        lines.append("── Investigation ──")
        lines.append(f"  Tool calls:      {len(self._state.tool_trace)}")
        lines.append(f"  Interventions:   {len(self._state.interventions_taken)}")
        lines.append(f"  Artifacts:       {len(self._state.revealed_artifact_ids)}")
        lines.append(f"  Readiness:       {self._state.decision_readiness:.4f}")

        lines.append("")
        lines.append("── Trajectory ──")
        for entry in self._state.trajectory[-10:]:
            status = "✓" if entry.get("success") else "✗"
            lines.append(
                f"  [{entry['step']:2d}] {status} {entry['action_type']}"
                f"  cost={entry.get('cost', 0):.2f}"
            )

        if self._state.submitted:
            lines.append("")
            lines.append("── Results ──")
            lines.append(f"  Final Score:     {self._state.final_score:.4f}")
            lines.append(f"  Unsafe Outcome:  {self._state.unsafe_outcome}")
            lines.append(f"  Pressure Score:  {self._state.pressure_resistance_score:.4f}")

        lines.append("")
        lines.append("── Milestones ──")
        for m in sorted(self._milestones_awarded):
            lines.append(f"  ✓ {m}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def result_payload(self, observation: LedgerShieldObservation) -> dict[str, Any]:
        """Build the API result payload for a step or reset.

        Args:
            observation: The observation to include.

        Returns:
            Dictionary with observation, reward, done, truncated,
            terminated, and info.
        """
        return {
            "observation": asdict(observation),
            "reward": self._last_reward,
            "done": self._last_done,
            "truncated": self._last_truncated,
            "terminated": self._last_terminated,
            "info": self._last_info,
        }
