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
        "[END] success=true steps=3 rewards=0.00,-0.01,0.99",
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
    }
    assert expected.issubset(set(inference.DEFAULT_CASES))
