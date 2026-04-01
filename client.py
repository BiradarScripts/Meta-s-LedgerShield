from __future__ import annotations

from typing import Any

from models import LedgerShieldAction, LedgerShieldObservation, LedgerShieldState
from openenv_compat import EnvClient, StepResult


class LedgerShieldEnv(EnvClient[LedgerShieldAction, LedgerShieldObservation, LedgerShieldState]):
    """
    Thin client wrapper for the LedgerShield OpenEnv-compatible HTTP server.
    """

    def _step_payload(self, action: LedgerShieldAction) -> dict[str, Any]:
        return {
            "action_type": action.action_type,
            "payload": action.payload,
        }

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[LedgerShieldObservation]:
        observation_payload = payload.get("observation", {}) or {}
        observation = LedgerShieldObservation(**observation_payload)

        return StepResult(
            observation=observation,
            reward=float(payload.get("reward", 0.0) or 0.0),
            done=bool(payload.get("done", False)),
            info=payload.get("info", {}) or {},
        )

    def _parse_state(self, payload: dict[str, Any]) -> LedgerShieldState:
        return LedgerShieldState(**payload)