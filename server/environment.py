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

from copy import deepcopy
import math
from dataclasses import asdict
import os
import random
import re
import uuid
from typing import Any

from models import LedgerShieldObservation, LedgerShieldReward, LedgerShieldState
from openenv_compat import Environment

from .compliance_engine import evaluate_compliance
from .currency_engine import validate_iban, validate_swift
from .curriculum import (
    CurriculumState,
    adjust_case_for_tier,
    curriculum_summary,
    select_next_case,
    update_curriculum,
)
from .data_loader import load_all
from .dual_agent_mode import (
    StackelbergAuditStrategy,
    WatchdogState,
    build_watchdog_observation,
    compute_stackelberg_equilibrium,
    score_dual_agent_episode,
    update_watchdog_state,
    watchdog_evaluate_decision,
)
from .reward_machine import (
    RewardMachineState,
    initialize_reward_machine,
    reward_machine_payload,
    transition_reward_machine,
)
from .categorical_composition import task_family_component
from .rl_export import export_state_vector
from .benchmark_contract import (
    BLIND_CONTROL_TRACK,
    CASE_TRACK,
    case_matches_track,
    case_track_metadata,
    normalize_track,
    track_description,
    track_label,
)
from .control_statechart import control_boundary_snapshot, evaluate_control_boundary
from .grading import score_submission
from .decision_certificate import build_decision_certificate, verify_decision_certificate
from .decision_falsifier import falsify_decision
from .institutional_game import (
    InstitutionalMemory,
    attach_institutional_context,
    evaluate_authority_gate,
    institutional_context_for_case,
    public_institutional_memory,
    record_trust_graph,
    record_institutional_outcome,
)
from .outcome_simulator import simulate_outcome
from .proper_scoring import resolve_predicted_probabilities
from .risk_rules import assess_submission_risk
from .schema import ALLOWED_ACTIONS, ALLOWED_DECISIONS, INTERVENTION_ACTIONS
from .sprt_engine import (
    DEFAULT_HYPOTHESES,
    SPRTState,
    infer_tool_observation,
    initialize_sprt,
    optimal_stopping_check,
    sprt_state_payload,
    update_sprt,
)
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
from .trust_graph import build_trust_graph
from .voi_engine import optimal_tool_selection, value_of_information
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

_CUSTOM_CASE_ID_RE = re.compile(r"^CUSTOM-[A-Z0-9]{2,16}$")

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
        self._curriculum_state = CurriculumState()
        self._watchdog_state = WatchdogState()
        self._sprt_runtime_state: SPRTState = initialize_sprt()
        self._reward_machine_runtime_state: RewardMachineState = initialize_reward_machine("task_a")
        self._institutional_memory = InstitutionalMemory.from_cases(self.db.get("cases", []))
        self._track_mode = os.getenv("LEDGERSHIELD_TRACK_MODE", "blind").strip().lower() or "blind"
        self._benchmark_track = CASE_TRACK

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
                            "predicted_probabilities": "dict[hypothesis,float] (optional)",
                            "decision_certificate": "Decision Certificate Graph (optional)",
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
                "sprt_state": {"type": "Dict"},
                "tool_rankings": {"type": "Dict"},
                "reward_machine": {"type": "Dict"},
                "institutional_memory": {"type": "Dict"},
            },
        }

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def state(self) -> LedgerShieldState:
        """Return the current internal state."""
        return self._state

    def public_state(self) -> dict[str, Any]:
        """Return the public (non-hidden) state snapshot."""
        state = public_state_snapshot(self._state, self._hidden_world)
        state["institutional_memory"] = public_institutional_memory(self._institutional_memory)
        state["control_boundary"] = control_boundary_snapshot(self._state, self._hidden_world)
        return state

    def institutional_memory(self) -> dict[str, Any]:
        """Return the persistent institutional memory/loss ledger."""
        return public_institutional_memory(self._institutional_memory)

    def reset_institutional_memory(self) -> dict[str, Any]:
        """Reset persistent portfolio memory without changing fixture data."""
        self._institutional_memory = InstitutionalMemory.from_cases(self.db.get("cases", []))
        return self.institutional_memory()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _normalize_custom_case_payload(
        self,
        raw: Any,
    ) -> dict[str, Any]:
        """Validate API ``custom_case`` and return normalized fields for cloning.

        Clones an existing benchmark case (template) and assigns a new ``case_id``
        plus instruction text. Document graphs and gold stay identical to the template.
        """
        if not isinstance(raw, dict):
            raise ValueError("custom_case must be a JSON object")
        template_id = raw.get("template_case_id")
        if template_id is None:
            template_id = raw.get("templateCaseId")
        if not isinstance(template_id, str) or not template_id.strip():
            raise ValueError("custom_case.template_case_id is required")
        template_id = template_id.strip()
        cases_by_id = self.db.get("cases_by_id") or {}
        if template_id not in cases_by_id:
            raise ValueError(f"unknown custom_case.template_case_id: {template_id}")

        case_id = raw.get("case_id")
        if case_id is None:
            case_id = raw.get("caseId")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("custom_case.case_id is required")
        case_id_norm = case_id.strip().upper()
        if not _CUSTOM_CASE_ID_RE.match(case_id_norm):
            raise ValueError(
                "custom_case.case_id must match CUSTOM- plus 2-16 uppercase letters/digits "
                "(example: CUSTOM-DEMO01)"
            )

        instruction = raw.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("custom_case.instruction is required (non-empty string)")
        instruction = instruction.strip()
        if "\n" in instruction or "\r" in instruction:
            raise ValueError("custom_case.instruction must be a single line (no newlines)")
        if len(instruction) > 800:
            raise ValueError("custom_case.instruction must be at most 800 characters")

        out: dict[str, Any] = {
            "template_case_id": template_id,
            "case_id": case_id_norm,
            "instruction": instruction,
        }

        if raw.get("max_steps") is not None or raw.get("maxSteps") is not None:
            ms = raw.get("max_steps", raw.get("maxSteps"))
            if isinstance(ms, bool):
                raise ValueError("custom_case.max_steps must be an integer")
            if isinstance(ms, int):
                ms_val = ms
            elif isinstance(ms, float) and ms.is_integer():
                ms_val = int(ms)
            else:
                raise ValueError("custom_case.max_steps must be an integer")
            if ms_val < 4 or ms_val > 50:
                raise ValueError("custom_case.max_steps must be between 4 and 50")
            out["max_steps"] = ms_val

        if raw.get("budget_total") is not None or raw.get("budgetTotal") is not None:
            bt = raw.get("budget_total", raw.get("budgetTotal"))
            if isinstance(bt, (int, float)):
                btf = float(bt)
            else:
                raise ValueError("custom_case.budget_total must be a number")
            if btf < 1.0 or btf > 50.0:
                raise ValueError("custom_case.budget_total must be between 1 and 50")
            out["budget_total"] = round(btf, 4)

        return out

    def _case_from_custom_spec(self, spec: dict[str, Any]) -> dict[str, Any]:
        template = self.db["cases_by_id"][spec["template_case_id"]]
        case = deepcopy(template)
        case["case_id"] = spec["case_id"]
        case["instruction"] = spec["instruction"]
        if "max_steps" in spec:
            case["max_steps"] = spec["max_steps"]
        if "budget_total" in spec:
            case["budget_total"] = spec["budget_total"]
        return case

    def _select_case(
        self,
        seed: int | None = None,
        case_id: str | None = None,
        track: str | None = None,
    ) -> dict[str, Any]:
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
        selection_seed = seed if seed is not None else self.rng.randint(0, 2**31 - 1)
        requested_track = normalize_track(track)
        candidate_cases = [
            case
            for case in self.db["cases"]
            if case_matches_track(case, requested_track)
        ] or list(self.db["cases"])
        selected = select_next_case(self._curriculum_state, candidate_cases, seed=selection_seed)
        return adjust_case_for_tier(selected, self._curriculum_state.tier)

    def _currency_validation_snapshot(self, submitted: dict[str, Any]) -> dict[str, Any]:
        assert self.current_case is not None
        task_type = str(self.current_case.get("task_type", ""))
        if task_type != "task_a":
            return {"applicable": False, "score": 1.0}

        gold_fields = (self.current_case.get("gold", {}) or {}).get("fields", {}) or {}
        extracted_fields = submitted.get("extracted_fields", {}) or {}

        expected_bank = str(gold_fields.get("bank_account", "") or "").strip()
        submitted_bank = str(extracted_fields.get("bank_account", "") or "").strip()
        expected_currency = str(gold_fields.get("currency", "") or "").strip().upper()
        submitted_currency = str(extracted_fields.get("currency", "") or "").strip().upper()

        checks: list[float] = []
        snapshot: dict[str, Any] = {"applicable": True, "format": "unknown"}
        if expected_currency:
            checks.append(float(submitted_currency == expected_currency))
            snapshot["expected_currency"] = expected_currency
            snapshot["submitted_currency"] = submitted_currency

        compact_expected = "".join(expected_bank.split()).upper()
        if expected_bank:
            checks.append(float(" ".join(submitted_bank.lower().split()) == " ".join(expected_bank.lower().split())))
            snapshot["expected_bank_account"] = expected_bank
            snapshot["submitted_bank_account"] = submitted_bank
            if compact_expected[:2].isalpha() and len(compact_expected) >= 15:
                snapshot["format"] = "iban"
                snapshot["validation"] = validate_iban(submitted_bank)
                checks.append(float(snapshot["validation"].get("valid", False)))
            elif len(compact_expected) in {8, 11} and compact_expected[:4].isalpha():
                snapshot["format"] = "swift"
                snapshot["validation"] = validate_swift(submitted_bank)
                checks.append(float(snapshot["validation"].get("valid", False)))

        snapshot["score"] = round(sum(checks) / len(checks), 4) if checks else 1.0
        if not checks:
            snapshot["applicable"] = False
        return snapshot

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
        extra_metadata: dict[str, Any] | None = None,
    ) -> LedgerShieldObservation:
        """Construct an observation from the current state.

        Args:
            tool_result: Result of the last tool call (if any).
            messages: List of messages to include in the observation.
            extra_metadata: Additional key-value pairs merged into case_metadata.
                Used by reset() to expose the MDPComponent categorical spec.

        Returns:
            LedgerShieldObservation dataclass.
        """
        assert self.current_case is not None
        base_metadata: dict[str, Any] = {
            "task_label": self.current_case.get("task_label", ""),
            "due_date_days": int(self.current_case.get("due_date_days", 14) or 14),
            "ashtg": "Adversarial Sequential Hypothesis Testing Game",
            "benchmark_identity": "Verified institutional control intelligence in enterprise AP workflows",
            "benchmark_track": self._benchmark_track,
            "benchmark_track_label": track_label(self._benchmark_track),
            "benchmark_track_description": track_description(self._benchmark_track),
            "official_tracks": list(self.current_case.get("official_tracks", [])),
        }
        if extra_metadata:
            base_metadata.update(extra_metadata)
        observation_track_mode = "blind" if self._benchmark_track == BLIND_CONTROL_TRACK else self._track_mode
        base_metadata["track_mode"] = observation_track_mode
        instrumented = observation_track_mode != "blind"
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
            case_metadata=base_metadata,
            portfolio_context=dict(self._hidden_world.get("campaign_context", {})),
            sprt_state=deepcopy(self._state.sprt_state) if instrumented else {},
            tool_rankings=deepcopy(self._state.tool_rankings) if instrumented else {},
            reward_machine=deepcopy(self._state.reward_machine_state) if instrumented else {},
            institutional_memory=public_institutional_memory(self._institutional_memory),
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

    def reset(
        self,
        seed: int | None = None,
        case_id: str | None = None,
        track: str | None = None,
        custom_case: dict[str, Any] | None = None,
    ) -> LedgerShieldObservation:
        """Reset the environment and load a new case.

        Args:
            seed: Optional seed for case selection.
            case_id: Optional specific case to load.
            custom_case: Optional dict to clone a template case under a new ``CUSTOM-…``
                id and instruction (validated); when set, ``case_id`` / ``seed`` selection
                for loading is ignored.

        Returns:
            Initial observation for the new episode.
        """
        if custom_case is not None:
            spec = self._normalize_custom_case_payload(custom_case)
            self.current_case = self._case_from_custom_spec(spec)
        else:
            self.current_case = self._select_case(seed=seed, case_id=case_id, track=track)
        self._benchmark_track = normalize_track(track or self.current_case.get("primary_track"))
        self._hidden_world = build_hidden_world(self.current_case)
        institutional_context = institutional_context_for_case(
            self.current_case,
            self.db.get("cases", []),
            self._institutional_memory,
        )
        attach_institutional_context(self._hidden_world, institutional_context)

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
        self._sprt_runtime_state = initialize_sprt(hypotheses=DEFAULT_HYPOTHESES)
        self._reward_machine_runtime_state = initialize_reward_machine(self._state.task_type)
        self._watchdog_state = WatchdogState(strategy=self._apply_stackelberg_strategy())
        self._state.calibration_running_average = 0.0

        # ── Categorical MDP Composition (Pillar 9) ────────────────────────
        # Load the MDPComponent for this task family. The component defines
        # the task's formal state/action spaces and temporal specification.
        # required_observations seeds the hidden world's required_actions so
        # milestone detection and VoI computation know what evidence the task
        # demands.
        mdp_component = task_family_component(self._state.task_type)
        self._mdp_component = mdp_component
        # Inject the component's required action-space into the hidden world
        # so that _check_milestones() can verify completion against the
        # categorical spec rather than a hard-coded list.
        if "required_actions" not in self._hidden_world or not self._hidden_world["required_actions"]:
            self._hidden_world["required_actions"] = sorted(mdp_component.action_space)

        self._refresh_ashtg_public_state()
        self._state.decision_readiness = round(decision_readiness(self._state, self._hidden_world), 4)

        tier_name = curriculum_summary(self._curriculum_state).get("tier_name", "unknown")
        mdp_spec = {
            "component_name": mdp_component.name,
            "action_space": sorted(mdp_component.action_space),
            "state_space": sorted(mdp_component.state_space),
            "required_observations": sorted(mdp_component.required_observations),
            "temporal_spec": mdp_component.temporal_spec,
        }
        benchmark_metadata = case_track_metadata(self.current_case)
        return self._observation(
            messages=[f"Loaded case {self._state.case_id} (curriculum: {tier_name})"],
            extra_metadata={
                "mdp_component": mdp_spec,
                "benchmark_track": self._benchmark_track,
                "benchmark_track_label": track_label(self._benchmark_track),
                "benchmark_track_description": track_description(self._benchmark_track),
                "official_tracks": benchmark_metadata["official_tracks"],
            },
        )

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
        vendor_index = self.db["vendors_by_key"]
        override_vendors = overrides.get("vendors_by_key") or overrides.get("vendors")
        if isinstance(override_vendors, dict):
            vendor_index = override_vendors
        elif isinstance(override_vendors, list):
            vendor_index = {
                normalize_text(vendor.get("vendor_key")): vendor
                for vendor in override_vendors
                if isinstance(vendor, dict) and vendor.get("vendor_key")
            } or vendor_index
        po_index = self.db["po_by_id"]
        override_pos = overrides.get("po_by_id") or overrides.get("po_records")
        if isinstance(override_pos, dict):
            po_index = override_pos
        elif isinstance(override_pos, list):
            po_index = {
                str(row.get("po_id")): row
                for row in override_pos
                if isinstance(row, dict) and row.get("po_id")
            } or po_index
        receipt_index = self.db["receipt_by_id"]
        override_receipts = overrides.get("receipt_by_id") or overrides.get("receipts")
        if isinstance(override_receipts, dict):
            receipt_index = override_receipts
        elif isinstance(override_receipts, list):
            receipt_index = {
                str(row.get("receipt_id")): row
                for row in override_receipts
                if isinstance(row, dict) and row.get("receipt_id")
            } or receipt_index
        email_threads = overrides.get("email_threads", self.db["email_threads"])

        dispatch_map = {
            "zoom": lambda: zoom_tool(self.current_case, payload),
            "get_doc_crop": lambda: get_doc_crop_tool(self.current_case, payload),
            "ocr": lambda: ocr_tool(self.current_case, payload),
            "lookup_vendor": lambda: lookup_vendor_tool(vendor_index, payload),
            "lookup_vendor_history": lambda: lookup_vendor_history_tool(
                overrides.get("vendor_history", self.db["vendor_history"]), payload),
            "lookup_policy": lambda: lookup_policy_tool(self.db["policy_by_id"], self.db["policy_rules"], payload),
            "lookup_po": lambda: lookup_po_tool(po_index, payload),
            "lookup_receipt": lambda: lookup_receipt_tool(receipt_index, payload),
            "search_ledger": lambda: search_ledger_tool(
                self.current_case, overrides.get("ledger_index", self.db["ledger_index"]), payload),
            "inspect_email_thread": lambda: inspect_email_thread_tool(
                self.current_case, email_threads, payload),
            "compare_bank_account": lambda: compare_bank_account_tool(vendor_index, payload),
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
            "sprt_recommendation": (self._state.sprt_state or {}).get("recommended_decision"),
        }

    def _voi_channel_for_action(self, action_type: str) -> str:
        return {
            "request_callback_verification": "callback_verification_result",
            "flag_duplicate_cluster_review": "duplicate_cluster_report",
            "request_bank_change_approval_chain": "bank_change_approval_chain",
            "request_po_reconciliation": "po_reconciliation_report",
            "request_additional_receipt_evidence": "receipt_reconciliation_report",
        }.get(action_type, action_type)

    def _available_rankable_actions(self) -> list[str]:
        return [
            action
            for action in ALLOWED_ACTIONS
            if action != "submit_decision"
        ]

    def _compute_tool_rankings(self) -> dict[str, Any]:
        available_actions = self._available_rankable_actions()
        channel_costs = {
            action: self._apply_cost(action, {})
            for action in available_actions
        }
        rankings: dict[str, dict[str, float | bool]] = {}
        best_action = ""
        best_voi = float("-inf")
        best_ratio = float("-inf")
        for action in available_actions:
            channel = self._voi_channel_for_action(action)
            selection = optimal_tool_selection(
                [channel],
                self._sprt_runtime_state,
                self._state.budget_remaining,
                {channel: channel_costs[action]},
            )
            channel_rank = selection["rankings"].get(channel, {})
            rankings[action] = {
                "channel": channel,
                "voi": float(channel_rank.get("voi", 0.0) or 0.0),
                "cost": float(channel_rank.get("cost", channel_costs[action]) or channel_costs[action]),
                "voi_cost_ratio": float(channel_rank.get("voi_cost_ratio", 0.0) or 0.0),
                "affordable": bool(channel_rank.get("affordable", True)),
            }
            if rankings[action]["voi_cost_ratio"] > best_ratio:
                best_action = action
                best_voi = rankings[action]["voi"]
                best_ratio = rankings[action]["voi_cost_ratio"]

        should_stop = optimal_stopping_check(
            self._sprt_runtime_state,
            self._state.budget_remaining,
            max_remaining_voi=best_voi,
            min_tool_cost=min(TOOL_COSTS.values()),
        )["should_stop"]
        return {
            "recommended_tool": best_action,
            "voi": round(best_voi, 4) if best_action else 0.0,
            "voi_cost_ratio": round(best_ratio, 4) if best_action else 0.0,
            "should_stop": should_stop,
            "rankings": rankings,
        }

    def _update_running_calibration(self) -> None:
        latent = str(self._hidden_world.get("latent_hypothesis", "safe") or "safe")
        posterior = (self._state.sprt_state or {}).get("posterior_probabilities", {})
        probability = float(posterior.get(latent, 0.0) or 0.0)
        history_length = max(0, self._state.step_count)
        if history_length <= 1:
            self._state.calibration_running_average = round(probability, 4)
            return
        previous_weight = history_length - 1
        running = (
            float(self._state.calibration_running_average) * previous_weight
            + probability
        ) / history_length
        self._state.calibration_running_average = round(running, 4)

    def _refresh_ashtg_public_state(self) -> None:
        self._state.sprt_state = sprt_state_payload(self._sprt_runtime_state)
        self._state.tool_rankings = self._compute_tool_rankings()
        stopping = optimal_stopping_check(
            self._sprt_runtime_state,
            self._state.budget_remaining,
            max_remaining_voi=float(self._state.tool_rankings.get("voi", 0.0) or 0.0),
            min_tool_cost=min(TOOL_COSTS.values()),
        )
        self._sprt_runtime_state.optimal_stopping_reached = bool(stopping["should_stop"])
        self._state.sprt_state = sprt_state_payload(self._sprt_runtime_state)
        self._state.reward_machine_state = reward_machine_payload(self._reward_machine_runtime_state)
        self._update_running_calibration()

    def _apply_stackelberg_strategy(self) -> StackelbergAuditStrategy:
        risky = bool(self.current_case and self.current_case.get("gold", {}).get("unsafe_if_pay"))
        analyst_payoffs = {
            "audit_payment": {"pay": -0.8 if risky else 0.7, "hold": 0.5, "needs_review": 0.55, "escalate_fraud": 0.6},
            "audit_identity": {"pay": -0.7 if risky else 0.5, "hold": 0.45, "needs_review": 0.5, "escalate_fraud": 0.65},
            "audit_duplicate": {"pay": -0.6 if risky else 0.45, "hold": 0.55, "needs_review": 0.52, "escalate_fraud": 0.58},
        }
        watchdog_payoffs = {
            "audit_payment": {"pay": 1.0 if risky else -0.1, "hold": 0.5, "needs_review": 0.45, "escalate_fraud": 0.75 if risky else -0.2},
            "audit_identity": {"pay": 0.9 if risky else -0.05, "hold": 0.4, "needs_review": 0.5, "escalate_fraud": 0.8 if risky else -0.15},
            "audit_duplicate": {"pay": 0.8 if risky else -0.05, "hold": 0.55, "needs_review": 0.5, "escalate_fraud": 0.7 if risky else -0.15},
        }
        return compute_stackelberg_equilibrium(analyst_payoffs, watchdog_payoffs)

    def _update_sprt_from_result(self, action_type: str, result: dict[str, Any]) -> None:
        channel = self._voi_channel_for_action(action_type)
        self._sprt_runtime_state = update_sprt(
            self._sprt_runtime_state,
            channel,
            result,
        )

    def _update_sprt_from_artifact(self, artifact: dict[str, Any]) -> None:
        artifact_id = str(artifact.get("artifact_id", "") or "")
        if not artifact_id:
            return
        self._sprt_runtime_state = update_sprt(
            self._sprt_runtime_state,
            artifact_id,
            artifact,
        )

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
        pre_boundary = evaluate_control_boundary(
            self._state,
            self._hidden_world,
            action_type=action_type,
            payload=payload,
        )

        self._state.step_count += 1
        self._state.case_clock += 1
        potential_before = state_potential(self._state, self._hidden_world)
        signals_before = len(self._state.observed_risk_signals)
        sprt_before = deepcopy(self._sprt_runtime_state)

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
        reward_metadata["control_boundary_phase"] = pre_boundary.get("phase")

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
            submitted["predicted_probabilities"] = resolve_predicted_probabilities(
                submitted,
                hypotheses=DEFAULT_HYPOTHESES,
                posterior_hint=(self._state.sprt_state or {}).get("posterior_probabilities"),
            )
            self._state.pressure_resistance_score = round(
                pressure_resistance_score(self._state, self._hidden_world, decision),
                4,
            )
            internal_system_state = system_state_snapshot(self._state, self._hidden_world)
            if not isinstance(submitted.get("decision_certificate"), dict):
                submitted["decision_certificate"] = build_decision_certificate(
                    submitted,
                    trajectory=self._state.trajectory,
                    final_state=internal_system_state,
                    case_context=self.current_case,
                    auto_generated=True,
                )
                submitted["_auto_decision_certificate"] = True

            authority_gate = evaluate_authority_gate(
                self._institutional_memory,
                case=self.current_case,
                submitted=submitted,
                final_state=internal_system_state,
                trajectory=self._state.trajectory,
            )
            control_boundary = deepcopy(pre_boundary)
            effective_submitted = deepcopy(submitted)
            if bool(control_boundary.get("blocking")):
                effective_submitted["decision"] = control_boundary.get("enforced_decision", "NEEDS_REVIEW")
            if bool(authority_gate.get("blocking")):
                effective_submitted["decision"] = authority_gate.get("enforced_decision", "NEEDS_REVIEW")
            if bool(authority_gate.get("requires_handoff")) and not effective_submitted.get("handoff_packet"):
                effective_submitted["handoff_packet"] = {
                    "reason": "authority_gate_restriction",
                    "recommended_action": effective_submitted.get("decision", "NEEDS_REVIEW"),
                    "authority_level": authority_gate.get("authority_level"),
                    "reasons": list(authority_gate.get("reasons", []) or []),
                }
            if bool(control_boundary.get("blocking")) and not effective_submitted.get("handoff_packet"):
                effective_submitted["handoff_packet"] = {
                    "reason": "control_boundary_restriction",
                    "recommended_action": effective_submitted.get("decision", "NEEDS_REVIEW"),
                    "phase": control_boundary.get("phase"),
                    "required_followups": list(control_boundary.get("required_followups", []) or []),
                    "reasons": list(control_boundary.get("reasons", []) or []),
                }
            if control_boundary.get("reasons"):
                boundary_note = (
                    f"Control boundary ({control_boundary.get('phase')}) enforced "
                    f"{effective_submitted.get('decision', 'NEEDS_REVIEW')}: "
                    + "; ".join(str(reason) for reason in control_boundary.get("reasons", []) or [])
                )
                existing_notes = str(effective_submitted.get("notes", "") or "").strip()
                effective_submitted["notes"] = boundary_note if not existing_notes else f"{existing_notes} {boundary_note}".strip()
            if authority_gate.get("reasons"):
                authority_note = (
                    f"Authority gate ({authority_gate.get('authority_level')}) enforced "
                    f"{effective_submitted.get('decision', 'NEEDS_REVIEW')}: "
                    + "; ".join(str(reason) for reason in authority_gate.get("reasons", []) or [])
                )
                existing_notes = str(effective_submitted.get("notes", "") or "").strip()
                effective_submitted["notes"] = authority_note if not existing_notes else f"{existing_notes} {authority_note}".strip()
            internal_system_state["authority_gate"] = deepcopy(authority_gate)
            internal_system_state["control_boundary"] = deepcopy(control_boundary)
            internal_system_state["submitted_decision"] = str(submitted.get("decision", "") or "")
            internal_system_state["effective_decision"] = str(effective_submitted.get("decision", "") or "")

            outcome = simulate_outcome(
                submitted=effective_submitted,
                trajectory=self._state.trajectory,
                hidden_world=self._hidden_world,
                final_state=internal_system_state,
            )

            compliance_result = evaluate_compliance(
                task_type=self._state.task_type,
                trajectory=self._state.trajectory,
                revealed_artifacts=internal_system_state.get("revealed_artifact_ids", []) or [],
                decision=str(effective_submitted.get("decision", decision)),
                gold=self.current_case["gold"],
                case_context=self.current_case,
            )
            currency_validation = self._currency_validation_snapshot(submitted)
            institutional_update = record_institutional_outcome(
                self._institutional_memory,
                case=self.current_case,
                submitted=effective_submitted,
                outcome=outcome,
                trajectory=self._state.trajectory,
                compliance=asdict(compliance_result),
                authority_gate=authority_gate,
            )
            institutional_memory_snapshot = institutional_update["institutional_memory"]
            institutional_loss_ledger = dict(institutional_memory_snapshot.get("loss_ledger", {}))
            outcome["institutional_metrics"] = institutional_loss_ledger
            outcome["institutional_update"] = institutional_update["case_update"]
            outcome["authority_gate"] = deepcopy(authority_gate)
            internal_system_state["institutional_memory"] = institutional_memory_snapshot
            internal_system_state["institutional_context"] = deepcopy(self._hidden_world.get("institutional_context", {}))
            internal_system_state["authority_gate"] = deepcopy(authority_gate)
            certificate_report = verify_decision_certificate(
                submitted.get("decision_certificate"),
                submitted=submitted,
                gold=self.current_case["gold"],
                final_state=internal_system_state,
                case_context=self.current_case,
                trajectory=self._state.trajectory,
                synthesize_if_missing=True,
            ).to_dict()
            falsifier_report = falsify_decision(
                submitted=submitted,
                gold=self.current_case["gold"],
                final_state=internal_system_state,
                certificate_report=certificate_report,
                trajectory=self._state.trajectory,
            )
            trust_graph = build_trust_graph(
                submitted=submitted,
                final_state=internal_system_state,
                case_context=self.current_case,
                certificate_report=certificate_report,
                institutional_memory=institutional_memory_snapshot,
            )
            record_trust_graph(
                self._institutional_memory,
                case=self.current_case,
                trust_graph=trust_graph,
                submitted=submitted,
                outcome=outcome,
                control_boundary=control_boundary,
            )
            institutional_memory_snapshot = public_institutional_memory(self._institutional_memory)
            institutional_loss_ledger = dict(institutional_memory_snapshot.get("loss_ledger", {}))
            outcome["institutional_metrics"] = institutional_loss_ledger
            internal_system_state["adversarial_falsifier"] = falsifier_report
            internal_system_state["trust_graph"] = trust_graph
            internal_system_state["institutional_memory"] = institutional_memory_snapshot

            submission_case_context = {
                **self.current_case,
                "sprt_state": deepcopy(self._state.sprt_state),
                "latent_hypothesis": self._hidden_world.get("latent_hypothesis"),
                "benchmark_track": self._benchmark_track,
            }
            final_score, breakdown = score_submission(
                task_type=self._state.task_type,
                submitted=submitted,
                gold=self.current_case["gold"],
                budget_penalty=budget_penalty,
                trajectory=self._state.trajectory,
                outcome=outcome,
                investigation_summary=self._investigation_summary(),
                final_state=internal_system_state,
                case_context=submission_case_context,
                compliance_result=compliance_result,
                currency_validation=currency_validation,
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
            self._state.institutional_metrics = institutional_loss_ledger
            self._state.decision_certificate_report = certificate_report

            public_system_state = public_state_snapshot(self._state, self._hidden_world)
            public_system_state["institutional_memory"] = institutional_memory_snapshot
            public_system_state["authority_gate"] = deepcopy(authority_gate)
            public_system_state["control_boundary"] = deepcopy(control_boundary)
            public_system_state["effective_decision"] = str(effective_submitted.get("decision", "") or "")

            done = True
            terminated = True  # Phase 3.2: decision submission is a true termination
            reward = final_score

            result = {
                "tool_name": "submit_decision",
                "success": True,
                "submission_received": True,
                "final_score": final_score,
                "score_breakdown": breakdown,
                "result_class": breakdown.get("result_class", "incorrect_resolution"),
                "control_satisfied_resolution": float(breakdown.get("control_satisfied_resolution", 0.0) or 0.0),
                "institutional_utility": float(breakdown.get("institutional_utility", 0.0) or 0.0),
                "risk_assessment": heuristic_risk,
                "triggered_risk_reasons": triggered,
                "unsafe_outcome": self._state.unsafe_outcome,
                "decision": decision,
                "effective_decision": effective_submitted.get("decision"),
                "predicted_probabilities": submitted["predicted_probabilities"],
                "outcome": outcome,
                "system_state": public_system_state,
                "compliance": asdict(compliance_result),
                "currency_validation": currency_validation,
                "decision_certificate_report": certificate_report,
                "adversarial_falsifier": falsifier_report,
                "trust_graph": trust_graph,
                "authority_gate": authority_gate,
                "control_boundary": control_boundary,
                "institutional_metrics": institutional_loss_ledger,
                "institutional_memory": institutional_memory_snapshot,
                "pressure_resistance_score": self._state.pressure_resistance_score,
                "benchmark_track": self._benchmark_track,
                "track_mode": "blind" if self._benchmark_track == BLIND_CONTROL_TRACK else self._track_mode,
                "message": (
                    "Decision submitted, authority gate enforced review fallback, and the result was graded."
                    if authority_gate.get("blocking") or control_boundary.get("blocking")
                    else "Decision submitted and graded."
                ),
                "cost": 0.0,
            }

            info = {
                "final_score": final_score,
                "score_breakdown": breakdown,
                "result_class": breakdown.get("result_class", "incorrect_resolution"),
                "control_satisfied_resolution": float(breakdown.get("control_satisfied_resolution", 0.0) or 0.0),
                "institutional_utility": float(breakdown.get("institutional_utility", 0.0) or 0.0),
                "unsafe_outcome": self._state.unsafe_outcome,
                "outcome": outcome,
                "system_state": public_system_state,
                "compliance": asdict(compliance_result),
                "currency_validation": currency_validation,
                "decision_certificate_report": certificate_report,
                "adversarial_falsifier": falsifier_report,
                "trust_graph": trust_graph,
                "authority_gate": authority_gate,
                "control_boundary": control_boundary,
                "institutional_metrics": institutional_loss_ledger,
                "institutional_memory": institutional_memory_snapshot,
                "pressure_resistance_score": self._state.pressure_resistance_score,
                "benchmark_track": self._benchmark_track,
                "track_mode": "blind" if self._benchmark_track == BLIND_CONTROL_TRACK else self._track_mode,
                "curriculum": curriculum_summary(self._curriculum_state),
            }
            reward_components = {"final_score": final_score}
            reward_metadata.update(
                {
                "unsafe_outcome": self._state.unsafe_outcome,
                "budget_penalty": round(budget_penalty, 4),
                "pressure_resistance_score": self._state.pressure_resistance_score,
                "latent_hypothesis": self._hidden_world.get("latent_hypothesis"),
                }
            )
            cost = 0.0
            messages = ["Decision submitted and graded."]

        elif action_type in INTERVENTION_ACTIONS:
            cost = self._apply_cost(action_type, payload)

            observed_before = len(self._state.observed_risk_signals)
            raw_result, messages = self._handle_intervention(action_type, payload)
            result, _ = self._normalize_tool_result(action_type, raw_result, cost)
            self._update_sprt_from_result(action_type, result)

            observed_after = len(self._state.observed_risk_signals)
            revealed_new_signals = max(0, observed_after - observed_before)
            if revealed_new_signals > 0:
                result["novel_signal_count"] = max(result.get("novel_signal_count", 0), revealed_new_signals)

            channel = self._voi_channel_for_action(action_type)
            voi_reward = value_of_information(channel, sprt_before, cost)
            info_value = voi_reward + cost
            reward = voi_reward
            info = {
                "tool_name": action_type,
                "success": result["success"],
                "intervention": True,
            }
            reward_components = {
                "voi_reward": round(voi_reward, 4),
                "information_value": round(info_value, 4),
                "cost_penalty": round(-cost, 4),
            }
            reward_metadata.update(
                {
                    "intervention": True,
                    "novel_signal_count": int(result.get("novel_signal_count", 0) or 0),
                    "observation_key": infer_tool_observation(channel, result),
                }
            )

        else:
            raw_result = self._dispatch_tool(action_type, payload)
            cost = self._apply_cost(action_type, payload)
            result, messages = self._normalize_tool_result(action_type, raw_result, cost)
            self._update_sprt_from_result(action_type, result)

            observed_after = len(self._state.observed_risk_signals)
            channel = self._voi_channel_for_action(action_type)
            voi_reward = value_of_information(channel, sprt_before, cost)
            info_value = voi_reward + cost
            failure_penalty = 0.0
            reward = voi_reward
            if not result["success"]:
                failure_penalty = -0.05
                reward += failure_penalty

            info = {
                "tool_name": action_type,
                "success": result["success"],
            }
            reward_components = {
                "voi_reward": round(voi_reward, 4),
                "information_value": round(info_value, 4),
                "cost_penalty": round(-cost, 4),
                "failure_penalty": failure_penalty,
            }
            reward_metadata.update(
                {
                    "novel_signal_count": int(result.get("novel_signal_count", 0) or 0),
                    "success": bool(result.get("success", False)),
                    "observation_key": infer_tool_observation(channel, result),
                }
            )

        self._state.budget_remaining = round(max(self._state.budget_remaining - cost, 0.0), 4)

        ready_artifacts, async_messages, async_signals = advance_pending_events(self._state, self._hidden_world)
        if ready_artifacts:
            for artifact in ready_artifacts:
                self._update_sprt_from_artifact(artifact)
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
            "control_boundary_phase": pre_boundary.get("phase"),
            "control_boundary_warnings": list(pre_boundary.get("warnings", []) or []),
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

        self._reward_machine_runtime_state, reward_machine_bonus = transition_reward_machine(
            self._reward_machine_runtime_state,
            action_type,
            success=bool(result.get("success", False)),
        )
        if reward_machine_bonus:
            reward += reward_machine_bonus
            reward_components["reward_machine_bonus"] = round(reward_machine_bonus, 4)

        watchdog_snapshot = public_state_snapshot(self._state, self._hidden_world)
        watchdog_observation = build_watchdog_observation(
            step=self._state.step_count,
            analyst_action=action_type,
            analyst_payload=payload,
            tool_result=result,
            state_snapshot=watchdog_snapshot,
        )
        self._watchdog_state = update_watchdog_state(self._watchdog_state, watchdog_observation)
        result.setdefault("control_boundary", deepcopy(pre_boundary))
        info.setdefault("control_boundary", deepcopy(pre_boundary))
        if action_type == "submit_decision" and result.get("success"):
            verdict = watchdog_evaluate_decision(
                self._watchdog_state,
                str(payload.get("decision", "")),
                list(self._state.observed_risk_signals),
                [entry.get("action_type", "") for entry in self._state.interventions_taken],
            )
            watchdog_summary = {
                "verdict": verdict.value,
                **score_dual_agent_episode(
                    self._state.final_score,
                    self._watchdog_state,
                    str(payload.get("decision", "")),
                    self.current_case["gold"],
                ),
            }
            result["watchdog"] = watchdog_summary
            info["watchdog"] = watchdog_summary
            reward_metadata["watchdog_verdict"] = verdict.value

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

        self._refresh_ashtg_public_state()
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
        if done and action_type == "submit_decision":
            update_curriculum(self._curriculum_state, self._state.task_type, self._state.final_score)
            info["curriculum"] = curriculum_summary(self._curriculum_state)
        if ready_artifacts:
            info["async_artifacts"] = ready_artifacts

        info["rl_data_plane"] = {
            "state_vector": export_state_vector(
                self._state,
                sprt_state=self._sprt_runtime_state,
                reward_machine_state=self._reward_machine_runtime_state,
                watchdog_suspicion_score=self._watchdog_state.suspicion_score,
                best_tool_voi=float(self._state.tool_rankings.get("voi", 0.0) or 0.0),
            ),
            "reward": reward,
            "terminal": done,
            "truncated": truncated,
        }

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
        lines.append(f"  SPRT Stop:       {bool((self._state.sprt_state or {}).get('optimal_stopping_reached', False))}")
        lines.append(f"  SPRT Recommend:  {(self._state.sprt_state or {}).get('recommended_decision', '')}")
        lines.append(f"  Reward Progress: {float((self._state.reward_machine_state or {}).get('progress_fraction', 0.0)):.4f}")

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
