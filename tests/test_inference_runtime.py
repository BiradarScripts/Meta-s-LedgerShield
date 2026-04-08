from __future__ import annotations

import inference
from server.data_loader import load_all


def test_model_capability_profile_separates_standard_strong_and_elite_models():
    weak = inference.get_model_capability_profile("gpt-3.5-turbo")
    strong = inference.get_model_capability_profile("gpt-4o")
    elite = inference.get_model_capability_profile("gpt-5.4")

    assert weak.tier == "standard"
    assert strong.tier == "strong"
    assert elite.tier == "elite"
    assert elite.capability_score > strong.capability_score > weak.capability_score
    assert elite.plan_mode != "coverage"
    assert elite.repair_level != "grounded"


def test_vendor_key_for_uses_normalized_vendor_name_instead_of_baked_mapping():
    assert (
        inference.vendor_key_for({"vendor_name": "EuroCaps Components GmbH"})
        == "eurocaps components gmbh"
    )


def test_task_c_investigation_candidates_add_vendor_history_and_policy_for_threshold_case():
    candidates = inference.build_investigation_candidates(
        "task_c",
        {
            "case_instruction": "Investigate whether this invoice amount was deliberately structured below the approval threshold.",
            "invoice_fields": {"vendor_name": "Northwind Industrial Supplies Pvt Ltd", "bank_account": "IN55NW000111222"},
        },
        vendor_key="northwind industrial supplies pvt ltd",
        po_id="",
        receipt_id="",
        invoice_total=4950.0,
        invoice_number="INV-SPLIT-A",
        proposed_bank_account="IN55NW000111222",
        email_doc_id="",
        executed_signatures=set(),
    )

    action_types = [candidate.action_type for candidate in candidates]
    assert action_types == [
        "lookup_vendor",
        "lookup_vendor_history",
        "lookup_policy",
        "search_ledger",
        "search_ledger",
        "compare_bank_account",
    ]


def test_task_d_investigation_candidates_include_po_and_receipt_when_available():
    candidates = inference.build_investigation_candidates(
        "task_d",
        {
            "case_instruction": "Inspect the invoice, email thread, vendor master, ledger, and policy.",
            "invoice_fields": {"vendor_name": "Northwind Industrial Supplies Pvt Ltd"},
            "invoice_records": [],
        },
        vendor_key="northwind industrial supplies pvt ltd",
        po_id="PO-2048",
        receipt_id="GRN-2048",
        invoice_total=2478.0,
        invoice_number="INV-2048-A",
        proposed_bank_account="IN99FAKE000999888",
        email_doc_id="THR-100",
        executed_signatures=set(),
    )

    action_types = [candidate.action_type for candidate in candidates]
    assert "lookup_po" in action_types
    assert "lookup_receipt" in action_types


def test_heuristic_task_b_infers_missing_receipt_from_failed_lookup_and_instruction():
    result = inference.heuristic_task_b(
        {
            "case_instruction": "Decide whether to pay or hold the invoice when receipt evidence is missing.",
            "invoice_doc_id": "INV-B-002",
            "invoice_fields": {"po_id": "PO-2049", "total": 2478.0},
            "invoice_evidence": {
                "po_id": {"doc_id": "INV-B-002", "page": 1, "bbox": [0, 0, 10, 10], "token_ids": ["bb3"]},
                "total": {"doc_id": "INV-B-002", "page": 1, "bbox": [0, 10, 10, 20], "token_ids": ["bb4"]},
            },
            "invoice_line_items": [],
            "invoice_line_tokens": [],
            "po": {},
            "receipt": None,
            "tool_failures": {"lookup_receipt": [{"payload": {"receipt_id": "GRN-2049"}, "error": "receipt not found"}]},
            "po_reconciliation_report": {},
            "receipt_reconciliation_report": {},
            "callback_result": {},
        }
    )

    assert result["decision"] == "HOLD"
    assert result["discrepancies"] == ["missing_receipt"]
    assert "missing_receipt" in result["evidence_map"]


def test_heuristic_task_b_ignores_receipt_lookup_failure_for_tax_only_review():
    result = inference.heuristic_task_b(
        {
            "case_instruction": "Verify tax calculations match between invoice and PO. Report any discrepancies.",
            "invoice_doc_id": "INV-B-005",
            "invoice_fields": {"po_id": "PO-5501", "receipt_id": "GRN-5501", "total": 595.0},
            "invoice_evidence": {
                "po_id": {"doc_id": "INV-B-005", "page": 1, "bbox": [0, 0, 10, 10], "token_ids": ["b53"]},
                "receipt_id": {"doc_id": "INV-B-005", "page": 1, "bbox": [0, 10, 10, 20], "token_ids": ["b54"]},
                "total": {"doc_id": "INV-B-005", "page": 1, "bbox": [0, 20, 10, 30], "token_ids": ["b57"]},
            },
            "invoice_line_items": [],
            "invoice_line_tokens": [],
            "po": None,
            "receipt": None,
            "tool_failures": {
                "lookup_po": [{"payload": {"po_id": "PO-5501"}, "error": "po not found"}],
                "lookup_receipt": [{"payload": {"receipt_id": "GRN-5501"}, "error": "receipt not found"}],
            },
            "po_reconciliation_report": {
                "details": {"status": "reconciled_clean", "expected_discrepancies": []}
            },
            "receipt_reconciliation_report": {},
            "callback_result": {},
        }
    )

    assert result["decision"] == "PAY"
    assert result["discrepancies"] == []
    assert result["policy_checks"]["three_way_match"] == "pass"
    assert "tax_check_cleared" in result["evidence_map"]


def test_build_intervention_candidates_adds_callback_for_threshold_review_case():
    candidates = inference.build_intervention_candidates(
        "task_c",
        {
            "ledger_hits": [],
            "ledger_search": {"exact_duplicate_count": 0, "near_duplicate_count": 0},
            "bank_compares": [],
            "email_thread": {},
            "case_instruction": "Investigate whether this invoice amount was deliberately structured below the approval threshold.",
            "observed_risk_signals": [],
        },
        {
            "decision": "NEEDS_REVIEW",
            "fraud_flags": ["approval_threshold_evasion"],
            "discrepancies": ["approval_threshold_evasion"],
            "confidence": 0.9,
        },
        executed_signatures=set(),
    )

    action_types = [candidate.action_type for candidate in candidates]
    assert "request_callback_verification" in action_types
    assert "flag_duplicate_cluster_review" in action_types


def test_build_intervention_candidates_adds_duplicate_review_after_risky_ledger_investigation():
    candidates = inference.build_intervention_candidates(
        "task_d",
        {
            "ledger_hits": [],
            "ledger_search": {"exact_duplicate_count": 0, "near_duplicate_count": 0, "top_hits": []},
            "bank_compares": [{"matched": False}],
            "email_thread": {},
            "case_instruction": "Inspect the invoice, email thread, vendor master, vendor history, ledger, and policy.",
            "observed_risk_signals": ["bank_account_mismatch"],
        },
        {
            "decision": "ESCALATE_FRAUD",
            "reason_codes": ["bank_override_attempt", "policy_bypass_attempt"],
            "confidence": 0.99,
        },
        executed_signatures=set(),
    )

    action_types = [candidate.action_type for candidate in candidates]
    assert "flag_duplicate_cluster_review" in action_types


def test_ranked_intervention_plan_prioritizes_duplicate_review_before_freeze_when_ledger_risk_exists():
    submission = {
        "decision": "ESCALATE_FRAUD",
        "reason_codes": ["bank_override_attempt", "policy_bypass_attempt"],
        "confidence": 0.99,
    }
    collected = {
        "ledger_hits": [],
        "ledger_search": {"exact_duplicate_count": 0, "near_duplicate_count": 0, "top_hits": []},
        "bank_compares": [{"matched": False}],
        "email_thread": {},
        "case_instruction": "Inspect the invoice, email thread, vendor master, vendor history, ledger, and policy.",
        "observed_risk_signals": ["bank_account_mismatch", "sender_domain_spoof"],
    }
    planned = inference.llm_plan_actions(
        None,
        task_type="task_d",
        phase="intervention",
        collected=collected,
        candidates=inference.build_intervention_candidates(
            "task_d",
            collected,
            submission,
            executed_signatures=set(),
        ),
        max_actions=5,
        current_submission=submission,
    )

    action_types = [candidate.action_type for candidate in planned]
    assert action_types.index("flag_duplicate_cluster_review") < action_types.index("freeze_vendor_profile")


def test_elite_llm_plan_actions_backfills_ranked_coverage_when_model_returns_too_few_actions(monkeypatch):
    class _DummyMessage:
        content = "{\"ordered_action_ids\":[\"A1\",\"A5\"]}"

    class _DummyChoice:
        message = _DummyMessage()

    class _DummyResponse:
        choices = [_DummyChoice()]
        usage = None

    monkeypatch.setattr(
        inference,
        "create_json_chat_completion",
        lambda *args, **kwargs: _DummyResponse(),
    )
    monkeypatch.setattr(
        inference,
        "current_model_profile",
        lambda: inference.get_model_capability_profile("gpt-5.4"),
    )

    planned = inference.llm_plan_actions(
        object(),
        task_type="task_c",
        phase="investigation",
        collected={
            "case_instruction": "Detect duplicates and likely fraud in a batch payment review case. Use the ledger and evidence.",
            "invoice_fields": {"bank_account": "IN99FAKE000999888"},
            "observed_risk_signals": [],
        },
        candidates=[
            inference.LedgerShieldAction("lookup_vendor", {"vendor_key": "northwind"}),
            inference.LedgerShieldAction("lookup_vendor_history", {"vendor_key": "northwind"}),
            inference.LedgerShieldAction(
                "search_ledger",
                {"vendor_key": "northwind", "invoice_number": "INV-2048-A", "amount": 2478.0},
            ),
            inference.LedgerShieldAction(
                "search_ledger",
                {"invoice_number": "INV-2048-A", "amount": 2478.0},
            ),
            inference.LedgerShieldAction(
                "compare_bank_account",
                {"vendor_key": "northwind", "proposed_bank_account": "IN99FAKE000999888"},
            ),
        ],
        max_actions=5,
    )

    assert len(planned) == 5
    assert sum(1 for action in planned if action.action_type == "search_ledger") == 2
    assert any(action.action_type == "lookup_vendor_history" for action in planned)


def test_update_collected_from_tool_result_captures_async_artifacts():
    collected = {
        "revealed_artifacts": {},
        "callback_result": {},
        "bank_change_approval_chain": {},
        "po_reconciliation_report": {},
        "receipt_reconciliation_report": {},
        "duplicate_cluster_report": {},
        "tool_failures": {},
    }
    action = inference.LedgerShieldAction(action_type="request_callback_verification", payload={})
    tool = {
        "tool_name": "request_callback_verification",
        "success": True,
        "async_artifacts": [
            {
                "artifact_id": "duplicate_cluster_report",
                "details": {"status": "cluster_detected", "gold_links": ["LED-131"]},
            }
        ],
    }

    inference.update_collected_from_tool_result(
        collected,
        action,
        tool,
        email_doc_id="",
    )

    assert "duplicate_cluster_report" in collected["revealed_artifacts"]
    assert collected["duplicate_cluster_report"]["details"]["status"] == "cluster_detected"


def test_run_local_baseline_passes_remaining_regression_cases():
    result = inference.run_local_baseline(
        ["CASE-B-005", "CASE-C-002", "CASE-C-003", "CASE-D-002", "CASE-D-006"],
        db=load_all(),
        emit_logs=False,
    )

    scores = {case["case_id"]: case["score"] for case in result["results"]}

    assert scores["CASE-B-005"] >= 0.85
    assert scores["CASE-C-002"] >= 0.85
    assert scores["CASE-C-003"] >= 0.85
    assert scores["CASE-D-002"] >= 0.85
    assert scores["CASE-D-006"] >= 0.85
