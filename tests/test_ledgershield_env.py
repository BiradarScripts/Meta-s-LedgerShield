from __future__ import annotations

from envs.ledgershield_env.models import LedgerShieldAction
from envs.ledgershield_env.server.environment import LedgerShieldEnvironment
from envs.ledgershield_env.server.grading import score_submission


def test_reset_does_not_leak_gold_state():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-A-001")
    assert obs.case_id == "CASE-A-001"
    assert not hasattr(env.state, "gold_summary")
    state_payload = env.result_payload(obs)
    assert "gold_summary" not in str(state_payload)


def test_vendor_history_tool_returns_history():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="lookup_vendor_history",
            payload={"vendor_key": "northwind-industrial"},
        )
    )
    history = obs.last_tool_result["history"]
    assert history
    assert history[0]["change_type"] == "bank_account_change_request"


def test_perfect_task_d_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    gold = env.current_case["gold"]
    submission = {
        "decision": gold["decision"],
        "reason_codes": list(gold["reason_codes"]),
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": "Would PAY if the bank account matched vendor master and the sender used the approved domain.",
    }
    score, breakdown = score_submission("task_d", submission, gold, budget_penalty=0.0)
    assert score > 0.95, breakdown


def test_unsafe_pay_is_penalized():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={"decision": "PAY"},
        )
    )
    payload = env.result_payload(obs)
    assert payload["done"] is True
    assert obs.last_tool_result["unsafe_outcome"] is True
