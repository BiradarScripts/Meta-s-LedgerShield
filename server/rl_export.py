from __future__ import annotations

from typing import Any

from models import LedgerShieldState

from .reward_machine import RewardMachineState
from .sprt_engine import DEFAULT_HYPOTHESES, SPRTState


def export_state_vector(
    state: LedgerShieldState,
    *,
    sprt_state: SPRTState,
    reward_machine_state: RewardMachineState,
    watchdog_suspicion_score: float,
    best_tool_voi: float,
) -> list[float]:
    vector: list[float] = []

    for hypothesis in DEFAULT_HYPOTHESES:
        if hypothesis == "safe":
            vector.append(0.0)
        else:
            vector.append(float(sprt_state.log_likelihood_ratios.get(hypothesis, 0.0)))

    for hypothesis in DEFAULT_HYPOTHESES:
        if hypothesis == "safe":
            vector.append(1.0 - float(sprt_state.posterior_probabilities.get("safe", 0.0)))
        else:
            vector.append(float(sprt_state.distance_to_boundary.get(hypothesis, 1.0)))

    vector.append(float(sprt_state.decision_ready))
    vector.append(float(best_tool_voi))
    vector.append(float(state.budget_remaining) / max(1.0, float(state.budget_total)))
    vector.append(float(state.step_count) / max(1.0, float(state.max_steps)))
    vector.append(float(reward_machine_state.progress_fraction))

    for index in range(6):
        vector.append(1.0 if reward_machine_state.state_id == index else 0.0)

    vector.append(float(watchdog_suspicion_score))
    vector.append(float(state.calibration_running_average))
    return [round(value, 6) for value in vector]
