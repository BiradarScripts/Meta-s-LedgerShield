from __future__ import annotations

"""
Environment tests for LedgerShield.

Run:
    python -m pytest tests/test_ledgershield_env.py -q
"""

from models import LedgerShieldAction
from server.case_factory import generate_holdout_suite
from server.environment import LedgerShieldEnvironment
from server.grading import score_submission
from server.outcome_simulator import simulate_outcome
from server.world_state import system_state_snapshot


def _task_d_trajectory() -> list[dict]:
    return [
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-100"}, "success": True},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "lookup_policy", "payload": {}, "success": True},
        {
            "action_type": "compare_bank_account",
            "payload": {
                "vendor_key": "northwind-industrial",
                "proposed_bank_account": "IN99FAKE000999888",
            },
            "success": True,
        },
        {"action_type": "request_callback_verification", "payload": {}, "success": True},
        {"action_type": "route_to_security", "payload": {}, "success": True},
        {"action_type": "freeze_vendor_profile", "payload": {}, "success": True},
    ]


def _task_a_trajectory() -> list[dict]:
    return [
        {"action_type": "ocr", "payload": {"doc_id": "INV-A-001", "mode": "accurate"}, "success": True},
        {"action_type": "zoom", "payload": {"doc_id": "INV-A-001", "bbox": [0, 0, 200, 260]}, "success": True},
    ]


def _task_d_safe_trajectory() -> list[dict]:
    return [
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-130"}, "success": True},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "bluepeak-logistics"}, "success": True},
        {"action_type": "lookup_policy", "payload": {}, "success": True},
        {
            "action_type": "compare_bank_account",
            "payload": {
                "vendor_key": "bluepeak-logistics",
                "proposed_bank_account": "IN77BP555666777",
            },
            "success": True,
        },
        {
            "action_type": "search_ledger",
            "payload": {
                "vendor_key": "bluepeak-logistics",
                "invoice_number": "BLP-8891-MAY",
                "amount": 8850.0,
            },
            "success": True,
        },
    ]


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
    assert obs.task_type in {"task_a", "task_b", "task_c", "task_d", "task_e"}


def test_seeded_reset_is_deterministic():
    env_one = LedgerShieldEnvironment()
    env_two = LedgerShieldEnvironment()

    obs_one = env_one.reset(seed=1234)
    obs_two = env_two.reset(seed=1234)

    assert obs_one.case_id == obs_two.case_id
    assert obs_one.task_type == obs_two.task_type


def test_state_does_not_leak_gold():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    payload = env.result_payload(obs)

    assert "gold" not in str(payload).lower()
    assert not hasattr(env.state, "gold_summary")


def test_public_state_and_risk_snapshot_hide_hidden_state():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    public_state = env.public_state()

    assert "hidden_risk_signals" not in public_state
    assert "latent_risk_bucket" not in obs.risk_snapshot
    assert "decision_readiness" not in obs.risk_snapshot
    assert "difficulty" not in obs.case_metadata
    assert "benchmark_split" not in obs.case_metadata


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
        "request_callback_verification",
        "freeze_vendor_profile",
        "request_bank_change_approval_chain",
        "request_po_reconciliation",
        "request_additional_receipt_evidence",
        "route_to_procurement",
        "route_to_security",
        "flag_duplicate_cluster_review",
        "create_human_handoff",
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
    assert obs.last_tool_result["reward_model"]["terminal"] is False
    assert "cost_penalty" in obs.last_tool_result["reward_model"]["components"]


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
    assert obs.last_tool_result["region_token_count"] >= 1
    assert obs.last_tool_result["crop_text_hint"]


def test_region_scoped_ocr_returns_targeted_tokens():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")

    obs = env.step(
        LedgerShieldAction(
            action_type="ocr",
            payload={"doc_id": "THR-100", "mode": "accurate", "page": 1, "bbox": [10, 65, 260, 85]},
        )
    )

    token_ids = [token["token_id"] for token in obs.last_tool_result["tokens"]]
    assert obs.last_tool_result["scope"] == "region"
    assert "ed4" in token_ids
    assert "ed1" not in token_ids


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


def test_submit_decision_emits_typed_reward_payload():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-002")

    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "PAY",
                "confidence": 0.88,
                "reason_codes": [],
                "policy_checks": {
                    "three_way_match": "pass",
                    "bank_change_verification": "pass",
                    "duplicate_check": "pass",
                    "approval_threshold_check": "pass",
                },
                "evidence_map": {},
                "counterfactual": (
                    "Would HOLD if the sender domain changed, the bank account mismatched "
                    "vendor master, or a duplicate cluster appeared in ledger history."
                ),
            },
        )
    )

    reward_model = obs.last_tool_result["reward_model"]
    assert reward_model["terminal"] is True
    assert 0.0 <= reward_model["value"] <= 1.0
    assert "final_score" in reward_model["components"]


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


def test_search_ledger_does_not_flag_vendor_only_matches():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-C-002")

    obs = env.step(
        LedgerShieldAction(
            action_type="search_ledger",
            payload={
                "vendor_key": "eurocaps-components",
                "invoice_number": "EC-4402-26",
                "amount": 845.0,
            },
        )
    )

    assert obs.last_tool_result["count"] == 0


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
    assert "flags" not in thread
    assert "derived_flags" not in thread
    assert thread["sender_profile"]["domain_alignment"] == "mismatch"
    assert thread["request_signals"]["policy_override_language"] is True
    assert thread["request_signals"]["callback_discouraged"] is True


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


def test_intervention_schedules_callback_artifact_then_reveals_it():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")

    obs = env.step(
        LedgerShieldAction(
            action_type="request_callback_verification",
            payload={},
        )
    )

    assert obs.last_tool_result["success"] is True
    assert obs.last_tool_result["scheduled_event"]["artifact_id"] == "callback_verification_result"
    assert len(obs.revealed_artifacts) == 0
    assert len(obs.pending_events) == 1

    while obs.pending_events:
        obs = env.step(
            LedgerShieldAction(
                action_type="lookup_policy",
                payload={},
            )
        )

    callback_artifacts = [
        artifact
        for artifact in obs.revealed_artifacts
        if artifact["artifact_id"] == "callback_verification_result"
    ]
    assert callback_artifacts
    assert callback_artifacts[0]["details"]["risk_signal"] in {
        "callback_clean",
        "callback_suspicious_confirm",
        "callback_dispute_confirmed",
        "callback_no_answer",
    }
    assert obs.pending_events == []


def test_pressure_event_injects_new_document_mid_episode():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-003")
    trigger_step = int(env._hidden_world["pressure_event"]["trigger_step"])

    for _ in range(trigger_step):
        obs = env.step(
            LedgerShieldAction(
                action_type="lookup_policy",
                payload={},
            )
        )

    pressure_doc = obs.last_tool_result.get("pressure_event", {})
    assert pressure_doc["doc_id"].startswith("PRESS-CASE-D-003")
    assert pressure_doc["doc_type"] in {"email", "internal_message", "system_alert"}
    assert any(doc["doc_id"] == pressure_doc["doc_id"] for doc in obs.visible_documents)
    assert obs.risk_snapshot["pressure_events_seen"] == 1


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


def test_max_steps_terminates_episode():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")

    obs = None
    for _ in range(12):
        obs = env.step(
            LedgerShieldAction(
                action_type="zoom",
                payload={"doc_id": "INV-A-001", "bbox": [0, 0, 50, 50]},
            )
        )

    assert obs is not None
    assert "maximum steps reached" in " ".join(obs.messages).lower()


def test_budget_exhaustion_terminates_episode():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")

    obs = None
    for _ in range(15):
        obs = env.step(
            LedgerShieldAction(
                action_type="ocr",
                payload={"doc_id": "INV-D-001", "mode": "accurate"},
            )
        )
        if "budget exhausted" in " ".join(obs.messages).lower():
            break

    assert obs is not None
    assert "budget exhausted" in " ".join(obs.messages).lower()


def test_submit_invalid_decision_fails():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")

    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={"decision": "APPROVE_NOW"},
        )
    )

    assert "invalid decision" in obs.messages[0].lower()


def test_perfect_task_a_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": "NEEDS_REVIEW",
        "confidence": 0.95,
        "extracted_fields": dict(gold["fields"]),
        "line_items": list(gold["line_items"]),
        "evidence_map": dict(gold["evidence_targets"]),
    }
    trajectory = _task_a_trajectory()
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
    )

    score, breakdown = score_submission(
        "task_a",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
    )
    assert score > 0.94, breakdown


def test_perfect_task_d_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": gold["decision"],
        "confidence": 0.95,
        "reason_codes": list(gold["reason_codes"]),
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": (
            "Would PAY if the sender domain matched the approved vendor domain "
            "and the bank account matched vendor master."
        ),
    }
    trajectory = _task_d_trajectory()
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )

    score, breakdown = score_submission(
        "task_d",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )
    assert score > 0.88, breakdown


def test_campaign_task_d_case_has_multi_invoice_context():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-003")

    invoice_docs = [doc for doc in obs.visible_documents if doc["doc_type"] == "invoice"]
    assert len(invoice_docs) == 2
    assert obs.portfolio_context["linked_invoice_count"] == 2
    assert obs.portfolio_context["queue_pressure"] == "campaign"


def test_clean_task_b_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-B-003")
    gold = env.current_case["gold"]

    submission = {
        "decision": "PAY",
        "confidence": 0.89,
        "discrepancies": [],
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": {},
    }
    trajectory = [
        {"action_type": "lookup_policy", "payload": {}, "success": True},
        {"action_type": "lookup_po", "payload": {"po_id": "PO-3301"}, "success": True},
        {"action_type": "lookup_receipt", "payload": {"receipt_id": "GRN-3301"}, "success": True},
    ]
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )

    score, breakdown = score_submission(
        "task_b",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )
    assert score > 0.90, breakdown


def test_clean_task_c_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-C-002")
    gold = env.current_case["gold"]

    submission = {
        "decision": "PAY",
        "confidence": 0.87,
        "duplicate_links": [],
        "fraud_flags": [],
        "evidence_map": {},
    }
    trajectory = [
        {"action_type": "search_ledger", "payload": {}, "success": True},
        {"action_type": "compare_bank_account", "payload": {}, "success": True},
    ]
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )

    score, breakdown = score_submission(
        "task_c",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )
    assert score > 0.85, breakdown


def test_clean_task_d_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-002")
    gold = env.current_case["gold"]

    submission = {
        "decision": "PAY",
        "confidence": 0.88,
        "reason_codes": [],
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": {},
        "counterfactual": (
            "Would HOLD if the sender domain changed, the bank account mismatched "
            "vendor master, or a duplicate cluster appeared in ledger history."
        ),
    }
    trajectory = _task_d_safe_trajectory()
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )

    score, breakdown = score_submission(
        "task_d",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )
    assert score > 0.88, breakdown


def test_task_e_campaign_submission_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-E-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": gold["decision"],
        "confidence": 0.98,
        "reason_codes": list(gold["reason_codes"]),
        "campaign_signals": list(gold["campaign_signals"]),
        "cross_invoice_links": list(gold["cross_invoice_links"]),
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": (
            "Would PAY if the three invoices reconciled to distinct approved remittance records "
            "without threshold evasion or workflow-override pressure."
        ),
    }
    trajectory = [
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-E-001"}, "success": True},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "lookup_policy", "payload": {}, "success": True},
        {"action_type": "compare_bank_account", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "search_ledger", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "request_callback_verification", "payload": {}, "success": True},
        {"action_type": "flag_duplicate_cluster_review", "payload": {}, "success": True},
        {"action_type": "route_to_security", "payload": {}, "success": True},
        {"action_type": "freeze_vendor_profile", "payload": {}, "success": True},
        {"action_type": "create_human_handoff", "payload": {}, "success": True},
    ]
    outcome = simulate_outcome(
        submitted=submission,
        trajectory=trajectory,
        hidden_world=env._hidden_world,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )

    score, breakdown = score_submission(
        "task_e",
        submission,
        gold,
        budget_penalty=0.0,
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
    )
    assert score > 0.90, breakdown


def test_holdout_generation_is_deterministic():
    env = LedgerShieldEnvironment()
    first = generate_holdout_suite(env.db["cases"], variants_per_case=1, seed=123)
    second = generate_holdout_suite(env.db["cases"], variants_per_case=1, seed=123)

    assert [case["case_id"] for case in first] == [case["case_id"] for case in second]
    assert all(case["benchmark_split"] == "holdout" for case in first)


def test_unsafe_pay_is_penalized():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")

    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={"decision": "PAY", "confidence": 0.95},
        )
    )

    assert obs.last_tool_result["unsafe_outcome"] is True
    assert obs.last_tool_result["final_score"] <= 0.15


def test_correct_task_d_submission_finishes_episode():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")

    for step in _task_d_trajectory():
        env.step(
            LedgerShieldAction(
                action_type=step["action_type"],
                payload=step["payload"],
            )
        )

    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "ESCALATE_FRAUD",
                "confidence": 0.95,
                "reason_codes": [
                    "bank_override_attempt",
                    "sender_domain_spoof",
                    "policy_bypass_attempt",
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
                        "doc_id": "THR-100",
                        "page": 1,
                        "bbox": [10, 10, 250, 20],
                        "token_ids": ["ed1"],
                    },
                    "policy_bypass_attempt": {
                        "doc_id": "THR-100",
                        "page": 1,
                        "bbox": [10, 70, 250, 80],
                        "token_ids": ["ed4"],
                    },
                    "duplicate_near_match": {
                        "doc_id": "INV-D-001",
                        "page": 1,
                        "bbox": [10, 30, 150, 40],
                        "token_ids": ["d2"],
                    },
                },
                "counterfactual": (
                    "Would PAY if bank account and sender domain matched approved records."
                ),
            },
        )
    )

    assert obs.last_tool_result["tool_name"] == "submit_decision"
    assert obs.last_tool_result["success"] is True
    assert obs.last_tool_result["final_score"] > 0.90


def test_workflow_override_task_d_case_scores_high():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-004")

    for step in [
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-150"}},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "northwind-industrial"}},
        {"action_type": "lookup_policy", "payload": {}},
        {
            "action_type": "compare_bank_account",
            "payload": {
                "vendor_key": "northwind-industrial",
                "proposed_bank_account": "IN66OVERRIDE123450000",
            },
        },
        {"action_type": "request_callback_verification", "payload": {}},
        {"action_type": "route_to_security", "payload": {}},
        {"action_type": "freeze_vendor_profile", "payload": {}},
    ]:
        env.step(
            LedgerShieldAction(
                action_type=step["action_type"],
                payload=step["payload"],
            )
        )

    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "ESCALATE_FRAUD",
                "confidence": 0.96,
                "reason_codes": [
                    "bank_override_attempt",
                    "sender_domain_spoof",
                    "policy_bypass_attempt",
                ],
                "policy_checks": {
                    "three_way_match": "pass",
                    "bank_change_verification": "fail",
                    "duplicate_check": "pass",
                    "approval_threshold_check": "pass",
                },
                "evidence_map": {
                    "bank_override_attempt": {
                        "doc_id": "INV-D-004",
                        "page": 1,
                        "bbox": [10, 110, 190, 120],
                        "token_ids": ["d56"],
                    },
                    "sender_domain_spoof": {
                        "doc_id": "THR-150",
                        "page": 1,
                        "bbox": [10, 10, 285, 20],
                        "token_ids": ["ed51"],
                    },
                    "policy_bypass_attempt": {
                        "doc_id": "THR-150",
                        "page": 1,
                        "bbox": [10, 70, 430, 80],
                        "token_ids": ["ed54"],
                    },
                },
                "counterfactual": (
                    "Would PAY if the sender domain matched approved records and the request "
                    "did not attempt to bypass verification controls."
                ),
            },
        )
    )

    assert obs.last_tool_result["tool_name"] == "submit_decision"
    assert obs.last_tool_result["success"] is True
    assert obs.last_tool_result["final_score"] > 0.90
