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
