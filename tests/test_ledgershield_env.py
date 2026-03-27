from __future__ import annotations

from envs.ledgershield_env.models import LedgerShieldAction
from envs.ledgershield_env.server.environment import LedgerShieldEnvironment
from envs.ledgershield_env.server.grading import score_submission


def test_reset_loads_specific_case():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-A-001")
    assert obs.case_id == "CASE-A-001"
    assert obs.task_type == "task_a"
    assert obs.instruction
    assert obs.visible_documents
    assert obs.budget_remaining > 0


def test_reset_random_case_works():
    env = LedgerShieldEnvironment()
    obs = env.reset(seed=42)
    assert obs.case_id.startswith("CASE-")
    assert obs.task_type in {"task_a", "task_b", "task_c", "task_d"}


def test_state_does_not_leak_gold():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    payload = env.result_payload(obs)

    assert "gold" not in str(payload).lower()
    assert not hasattr(env.state, "gold_summary")


def test_allowed_actions_exist_in_observation():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    expected = {
        "zoom",
        "get_doc_crop",
        "ocr",
        "lookup_vendor",
        "lookup_vendor_history",
        "lookup_policy",
        "lookup_po",
        "lookup_receipt",
        "search_ledger",
        "inspect_email_thread",
        "compare_bank_account",
        "submit_decision",
    }
    assert set(obs.allowed_actions) == expected


def test_ocr_tool_returns_tokens():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="ocr",
            payload={"doc_id": "INV-A-001", "mode": "accurate"},
        )
    )
    assert obs.last_tool_result["tool_name"] == "ocr"
    assert obs.last_tool_result["success"] is True
    assert len(obs.last_tool_result["tokens"]) > 0


def test_get_doc_crop_tool_returns_crop_context():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="get_doc_crop",
            payload={"doc_id": "INV-D-001", "page": 1, "bbox": [10, 100, 180, 125]},
        )
    )
    assert obs.last_tool_result["tool_name"] == "get_doc_crop"
    assert obs.last_tool_result["success"] is True
    assert obs.last_tool_result["doc_id"] == "INV-D-001"


def test_lookup_vendor_returns_master_data():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="lookup_vendor",
            payload={"vendor_key": "northwind-industrial"},
        )
    )
    vendor = obs.last_tool_result["vendor"]
    assert vendor["vendor_key"] == "northwind-industrial"
    assert "bank_account" in vendor


def test_lookup_vendor_history_returns_history():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="lookup_vendor_history",
            payload={"vendor_key": "northwind-industrial"},
        )
    )
    history = obs.last_tool_result["history"]
    assert len(history) >= 1
    assert history[0]["change_type"] == "bank_account_change_request"


def test_lookup_po_returns_po():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="lookup_po",
            payload={"po_id": "PO-2048"},
        )
    )
    po = obs.last_tool_result["po"]
    assert po["po_id"] == "PO-2048"
    assert po["vendor_key"] == "northwind-industrial"


def test_lookup_receipt_returns_receipt():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="lookup_receipt",
            payload={"receipt_id": "GRN-2048"},
        )
    )
    receipt = obs.last_tool_result["receipt"]
    assert receipt["receipt_id"] == "GRN-2048"


def test_search_ledger_finds_duplicate_candidate():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="search_ledger",
            payload={
                "vendor_key": "northwind-industrial",
                "invoice_number": "INV-2048-A",
                "amount": 2478.0,
            },
        )
    )
    assert obs.last_tool_result["count"] >= 1
    hits = obs.last_tool_result["hits"]
    assert any(hit["ledger_id"] == "LED-131" for hit in hits)


def test_inspect_email_thread_returns_flags():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="inspect_email_thread",
            payload={"thread_id": "THR-100"},
        )
    )
    thread = obs.last_tool_result["thread"]
    assert thread["thread_id"] == "THR-100"
    assert "sender_domain_spoof" in thread["flags"]


def test_compare_bank_account_detects_mismatch():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="compare_bank_account",
            payload={
                "vendor_key": "northwind-industrial",
                "proposed_bank_account": "IN99FAKE000999888",
            },
        )
    )
    assert obs.last_tool_result["matched"] is False


def test_invalid_action_is_rejected():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="not_a_real_action",  # type: ignore[arg-type]
            payload={},
        )
    )
    assert "not allowed" in obs.messages[0].lower()


def test_budget_decreases_after_tool_use():
    env = LedgerShieldEnvironment()
    obs1 = env.reset(case_id="CASE-A-001")
    before = obs1.budget_remaining
    obs2 = env.step(
        LedgerShieldAction(
            action_type="ocr",
            payload={"doc_id": "INV-A-001", "mode": "accurate"},
        )
    )
    after = obs2.budget_remaining
    assert after < before


def test_submit_invalid_decision_fails():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={"decision": "APPROVE_NOW"},  # invalid
        )
    )
    assert "invalid decision" in obs.messages[0].lower()


def test_perfect_task_a_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": "NEEDS_REVIEW",
        "extracted_fields": dict(gold["extracted_fields"]),
        "line_items": list(gold["line_items"]),
        "evidence_map": dict(gold["evidence_targets"]),
    }
    score, breakdown = score_submission("task_a", submission, gold, budget_penalty=0.0)
    assert score > 0.95, breakdown


def test_perfect_task_d_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": gold["decision"],
        "reason_codes": list(gold["reason_codes"]),
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": "Would PAY if the sender domain matched the approved vendor domain and the bank account matched vendor master.",
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
    assert obs.last_tool_result["unsafe_outcome"] is True
    assert obs.last_tool_result["score"] <= 0.15


def test_correct_task_d_submission_finishes_episode():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "ESCALATE_FRAUD",
                "reason_codes": [
                    "bank_override_attempt",
                    "sender_domain_spoof",
                    "duplicate_near_match",
                ],
                "policy_checks": {
                    "three_way_match": "pass",
                    "bank_change_verification": "fail",
                    "duplicate_check": "fail",
                    "approval_threshold_check": "pass",
                },
                "evidence_map": {
                    "bank_override_attempt": {
                        "doc_id": "INV-D-001",
                        "page": 1,
                        "bbox": [10, 110, 170, 120],
                        "token_ids": ["d6"],
                    },
                    "sender_domain_spoof": {
                        "doc_id": "EM-D-001",
                        "page": 1,
                        "bbox": [10, 10, 250, 20],
                        "token_ids": ["ed1"],
                    },
                    "duplicate_near_match": {
                        "doc_id": "INV-D-001",
                        "page": 1,
                        "bbox": [10, 30, 150, 40],
                        "token_ids": ["d2"],
                    },
                },
                "counterfactual": "Would PAY if bank account and sender domain matched approved records.",
            },
        )
    )
    assert obs.last_tool_result["tool_name"] == "submit_decision"
    assert obs.last_tool_result["success"] is True
    assert obs.last_tool_result["score"] > 0.90