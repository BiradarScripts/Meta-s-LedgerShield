from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schema import normalize_text


TASK_MARKERS: dict[str, list[str]] = {
    "task_a": ["ocr", "zoom", "submit_decision"],
    "task_b": ["lookup_policy", "lookup_po", "lookup_receipt", "submit_decision"],
    "task_c": ["search_ledger", "compare_bank_account", "submit_decision"],
    "task_d": [
        "inspect_email_thread",
        "lookup_vendor_history",
        "compare_bank_account",
        "request_callback_verification",
        "submit_decision",
    ],
    "task_e": [
        "inspect_email_thread",
        "search_ledger",
        "compare_bank_account",
        "request_callback_verification",
        "route_to_security",
        "submit_decision",
    ],
}


@dataclass
class RewardMachineState:
    task_type: str
    state_id: int = 0
    completed_markers: list[str] = field(default_factory=list)
    progress_fraction: float = 0.0
    accepting: bool = False
    rejecting: bool = False


def initialize_reward_machine(task_type: str) -> RewardMachineState:
    return RewardMachineState(task_type=normalize_text(task_type))


def _next_expected_marker(state: RewardMachineState) -> str | None:
    markers = TASK_MARKERS.get(state.task_type, [])
    if state.state_id >= len(markers):
        return None
    return markers[state.state_id]


def transition_reward_machine(
    state: RewardMachineState,
    action_type: str,
    *,
    success: bool = True,
) -> tuple[RewardMachineState, float]:
    action = normalize_text(action_type)
    markers = TASK_MARKERS.get(state.task_type, [])
    expected = _next_expected_marker(state)
    reward = 0.0

    if not success:
        reward = -0.01
        return state, reward

    if expected and action == expected:
        state.completed_markers.append(action)
        state.state_id += 1
        reward = 0.02
    elif action == "submit_decision" and state.progress_fraction < 0.5:
        state.rejecting = True
        reward = -0.02
    elif action in markers and action not in state.completed_markers:
        state.completed_markers.append(action)
        reward = 0.01

    total_markers = max(len(markers), 1)
    completed = len({normalize_text(marker) for marker in state.completed_markers})
    state.progress_fraction = round(min(1.0, completed / total_markers), 4)
    state.accepting = bool(markers) and completed >= len(markers)
    return state, reward


def reward_machine_payload(state: RewardMachineState) -> dict[str, Any]:
    return {
        "task_type": state.task_type,
        "state_id": state.state_id,
        "completed_markers": list(state.completed_markers),
        "progress_fraction": state.progress_fraction,
        "accepting": state.accepting,
        "rejecting": state.rejecting,
    }
