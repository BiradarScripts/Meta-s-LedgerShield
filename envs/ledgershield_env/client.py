from __future__ import annotations

from .models import LedgerShieldAction, LedgerShieldObservation, LedgerShieldState
from .openenv_compat import EnvClient, StepResult


class LedgerShieldEnv(EnvClient[LedgerShieldAction, LedgerShieldObservation, LedgerShieldState]):
    def _step_payload(self, action: LedgerShieldAction) -> dict:
        return {"action_type": action.action_type, "payload": action.payload}

    def _parse_result(self, payload: dict) -> StepResult[LedgerShieldObservation]:
        observation = LedgerShieldObservation(**payload["observation"])
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
            info=payload.get("info", {}),
        )

    def _parse_state(self, payload: dict) -> LedgerShieldState:
        return LedgerShieldState(**payload)
