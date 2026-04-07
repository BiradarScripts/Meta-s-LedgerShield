from __future__ import annotations

import io
from contextlib import redirect_stdout

import inference


def test_log_helpers_emit_required_stdout_format():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        inference.log_start(task="CASE-X-001", env="ledgershield", model="openai/gpt-4.1-mini")
        inference.log_step(
            step=3,
            action="lookup_policy({})",
            reward=0.0,
            done=False,
            error=None,
        )
        inference.log_end(success=True, steps=3, rewards=[0.0, -0.01, 0.99])

    lines = buffer.getvalue().splitlines()
    assert lines == [
        "[START] task=CASE-X-001 env=ledgershield model=openai/gpt-4.1-mini",
        "[STEP] step=3 action=lookup_policy({}) reward=0.00 done=false error=null",
        "[END] success=true steps=3 score=0.99 rewards=0.00,-0.01,0.99",
    ]


def test_sanitize_log_field_normalizes_whitespace():
    assert inference.sanitize_log_field(None) == "null"
    assert inference.sanitize_log_field("a  b\nc") == "a b c"


def test_default_cases_cover_clean_and_adversarial_paths():
    expected = {
        "CASE-B-003",
        "CASE-C-002",
        "CASE-D-002",
        "CASE-D-001",
        "CASE-D-003",
        "CASE-D-004",
        "CASE-E-001",
    }
    assert expected.issubset(set(inference.DEFAULT_CASES))


def test_email_thread_signal_derivation_uses_structured_email_view():
    signals = inference.derive_email_thread_signals(
        {
            "sender_profile": {"domain_alignment": "mismatch"},
            "request_signals": {
                "bank_change_language": True,
                "callback_discouraged": True,
                "policy_override_language": False,
                "urgency_language": True,
            },
        }
    )

    assert {
        "sender_domain_spoof",
        "bank_override_attempt",
        "policy_bypass_attempt",
        "urgent_payment_pressure",
    }.issubset(signals)


def test_summarize_case_trials_tracks_consistent_pass():
    summary = inference.summarize_case_trials(
        "CASE-D-001",
        [
            {"case_id": "CASE-D-001", "task_type": "task_d", "score": 0.91, "steps": 8, "final_decision": "ESCALATE_FRAUD"},
            {"case_id": "CASE-D-001", "task_type": "task_d", "score": 0.88, "steps": 9, "final_decision": "ESCALATE_FRAUD"},
            {"case_id": "CASE-D-001", "task_type": "task_d", "score": 0.79, "steps": 9, "final_decision": "HOLD"},
        ],
        pass_threshold=0.85,
    )

    assert summary["trial_pass_rate"] == 0.6667
    assert summary["pass_k_consistent"] is False
    assert summary["pass_k_any"] is True
    assert summary["final_decision"] == "ESCALATE_FRAUD"
