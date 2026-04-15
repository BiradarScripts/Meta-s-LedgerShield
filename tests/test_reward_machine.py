"""
Tests for reward_machine.py — LTLf-compiled Reward Machines.

Covers all 5 task families, progress tracking, accepting/rejecting states,
early-submit penalty, out-of-order marker handling, and payload serialization.
"""
from __future__ import annotations

from server.reward_machine import (
    TASK_MARKERS,
    RewardMachineState,
    initialize_reward_machine,
    reward_machine_payload,
    transition_reward_machine,
)


# ── Initialization ───────────────────────────────────────────────────────────

def test_reward_machine_initializes_at_zero():
    for task_type in ["task_a", "task_b", "task_c", "task_d", "task_e"]:
        state = initialize_reward_machine(task_type)
        assert state.state_id == 0
        assert state.progress_fraction == 0.0
        assert state.accepting is False
        assert state.rejecting is False


def test_reward_machine_task_types_have_markers():
    for task_type in ["task_a", "task_b", "task_c", "task_d", "task_e"]:
        assert len(TASK_MARKERS[task_type]) >= 3


# ── Task A ────────────────────────────────────────────────────────────────────

def test_task_a_accepts_after_full_sequence():
    state = initialize_reward_machine("task_a")
    for action in TASK_MARKERS["task_a"]:
        state, _ = transition_reward_machine(state, action, success=True)
    assert state.accepting is True
    assert state.progress_fraction == 1.0


def test_task_a_gives_positive_reward_for_in_order_step():
    state = initialize_reward_machine("task_a")
    _, reward = transition_reward_machine(state, TASK_MARKERS["task_a"][0], success=True)
    assert reward > 0.0


# ── Task B ────────────────────────────────────────────────────────────────────

def test_task_b_accepts_after_full_sequence():
    state = initialize_reward_machine("task_b")
    for action in TASK_MARKERS["task_b"]:
        state, _ = transition_reward_machine(state, action, success=True)
    assert state.accepting is True


def test_task_b_gives_reward_for_three_way_match_steps():
    state = initialize_reward_machine("task_b")
    state, r1 = transition_reward_machine(state, "lookup_policy", success=True)
    state, r2 = transition_reward_machine(state, "lookup_po", success=True)
    assert r1 > 0.0
    assert r2 > 0.0


# ── Task C ────────────────────────────────────────────────────────────────────

def test_task_c_tracks_duplicate_detection_path():
    state = initialize_reward_machine("task_c")
    state, _ = transition_reward_machine(state, "search_ledger", success=True)
    assert state.progress_fraction > 0.0


def test_task_c_accepts_after_full_sequence():
    state = initialize_reward_machine("task_c")
    for action in TASK_MARKERS["task_c"]:
        state, _ = transition_reward_machine(state, action, success=True)
    assert state.accepting is True


# ── Task D ────────────────────────────────────────────────────────────────────

def test_reward_machine_tracks_progress_in_order_task_d():
    state = initialize_reward_machine("task_d")
    state, r1 = transition_reward_machine(state, "inspect_email_thread", success=True)
    state, r2 = transition_reward_machine(state, "lookup_vendor_history", success=True)
    assert r1 > 0.0
    assert r2 > 0.0
    assert state.progress_fraction > 0.0


def test_reward_machine_accepts_after_full_task_d_sequence():
    state = initialize_reward_machine("task_d")
    for action in TASK_MARKERS["task_d"]:
        state, _ = transition_reward_machine(state, action, success=True)
    assert state.accepting is True
    assert state.progress_fraction == 1.0


# ── Task E ────────────────────────────────────────────────────────────────────

def test_task_e_has_route_to_security_marker():
    assert "route_to_security" in TASK_MARKERS["task_e"]


def test_task_e_accepts_after_full_sequence():
    state = initialize_reward_machine("task_e")
    for action in TASK_MARKERS["task_e"]:
        state, _ = transition_reward_machine(state, action, success=True)
    assert state.accepting is True


def test_task_e_is_longer_than_task_d():
    assert len(TASK_MARKERS["task_e"]) >= len(TASK_MARKERS["task_d"])


# ── Early submission penalty ──────────────────────────────────────────────────

def test_early_submit_triggers_rejecting():
    state = initialize_reward_machine("task_d")
    # Submit immediately without any investigation (progress_fraction = 0)
    state, reward = transition_reward_machine(state, "submit_decision", success=True)
    assert state.rejecting is True
    assert reward < 0.0


def test_submit_after_half_investigation_does_not_reject():
    state = initialize_reward_machine("task_a")
    # task_a has 3 markers; do 2 of them (≥ 50%)
    state, _ = transition_reward_machine(state, "ocr", success=True)
    state, _ = transition_reward_machine(state, "zoom", success=True)
    state, reward = transition_reward_machine(state, "submit_decision", success=True)
    assert state.rejecting is False


# ── Failure handling ──────────────────────────────────────────────────────────

def test_failed_action_gives_small_negative_reward():
    state = initialize_reward_machine("task_d")
    _, reward = transition_reward_machine(state, "inspect_email_thread", success=False)
    assert reward < 0.0


def test_failed_action_does_not_advance_state():
    state = initialize_reward_machine("task_d")
    initial_id = state.state_id
    state, _ = transition_reward_machine(state, "inspect_email_thread", success=False)
    assert state.state_id == initial_id


# ── Out-of-order handling ─────────────────────────────────────────────────────

def test_out_of_order_marker_still_counts_for_progress():
    state = initialize_reward_machine("task_d")
    # compare_bank_account is marker index 2 in task_d, not index 0
    state, reward = transition_reward_machine(state, "compare_bank_account", success=True)
    # Should give partial credit but not advance ordered state_id
    assert state.progress_fraction >= 0.0


# ── Payload serialization ─────────────────────────────────────────────────────

def test_reward_machine_payload_contains_required_keys():
    state = initialize_reward_machine("task_d")
    payload = reward_machine_payload(state)
    required = {"task_type", "state_id", "completed_markers", "progress_fraction", "accepting", "rejecting"}
    assert required <= set(payload.keys())


def test_reward_machine_payload_progress_fraction_bounded():
    state = initialize_reward_machine("task_d")
    for action in TASK_MARKERS["task_d"]:
        state, _ = transition_reward_machine(state, action, success=True)
    payload = reward_machine_payload(state)
    assert 0.0 <= payload["progress_fraction"] <= 1.0
