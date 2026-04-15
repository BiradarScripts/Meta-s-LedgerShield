from __future__ import annotations

from models import LedgerShieldState
from server.reward_machine import initialize_reward_machine
from server.rl_export import export_state_vector
from server.sprt_engine import initialize_sprt, update_sprt


def test_rl_export_state_vector_has_expected_dimension():
    state = LedgerShieldState(budget_total=10.0, budget_remaining=8.0, max_steps=20, step_count=2, calibration_running_average=0.4)
    sprt = initialize_sprt()
    sprt = update_sprt(sprt, "compare_bank_account", {"matched": False})
    reward_machine = initialize_reward_machine("task_d")
    vector = export_state_vector(
        state,
        sprt_state=sprt,
        reward_machine_state=reward_machine,
        watchdog_suspicion_score=0.2,
        best_tool_voi=0.35,
    )

    assert len(vector) == 37
    assert vector[25] == 0.35
