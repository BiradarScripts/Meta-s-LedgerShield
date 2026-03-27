from __future__ import annotations
from typing import Any

from openenv.core import EnvClient, StepResult
from .models import LedgerShieldAction, LedgerShieldObservation, LedgerShieldState

class LedgerShieldEnv(EnvClient[LedgerShieldAction, LedgerShieldObservation, LedgerShieldState]):
    
    def _step_payload(self, action: LedgerShieldAction) -> dict[str, Any]:
        """Formats the action into a JSON-serializable dict for the server."""
        return {
            "action_type": action.action_type,
            "payload": action.payload,
        }

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[LedgerShieldObservation]:
        """Parses the server's response back into an Observation and StepResult."""
        observation = LedgerShieldObservation(**payload.get("observation", {}))
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
            info=payload.get("info", {}),
        )

    def _parse_state(self, payload: dict[str, Any]) -> LedgerShieldState:
        """Parses the internal state returned by the server."""
        return LedgerShieldState(**payload)