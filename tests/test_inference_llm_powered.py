from __future__ import annotations

import inference_llm_powered


def test_derive_email_thread_from_ocr_uses_vendor_domains_when_thread_lookup_is_missing():
    thread = inference_llm_powered.derive_email_thread_from_ocr(
        {
            "email_doc_id": "THR-E-SC-001",
            "email_tokens": [
                {"token_id": "e1", "text": "From: billing@eurocaps-components.example.net", "page": 1, "bbox": [0, 0, 10, 10]},
                {"token_id": "e2", "text": "Subject: Updated bank details for all future payments", "page": 1, "bbox": [0, 10, 10, 20]},
                {"token_id": "e3", "text": "Our banking partner has changed. All payments should be directed to DE00COMPROMISED999.", "page": 1, "bbox": [0, 20, 10, 30]},
                {"token_id": "e4", "text": "Please do not contact our old banking team as they no longer handle our account.", "page": 1, "bbox": [0, 30, 10, 40]},
            ],
            "vendor": {
                "vendor_key": "eurocaps-components",
                "vendor_name": "EuroCaps Components GmbH",
                "approved_domains": ["eurocaps.example.de"],
            },
            "invoice_fields": {"vendor_name": "EuroCaps Components GmbH"},
        }
    )

    assert thread["sender_profile"]["domain_alignment"] == "mismatch"
    assert thread["sender_profile"]["expected_domain"] == "eurocaps.example.de"
    assert "sender_domain_spoof" in thread["derived_flags"]
    assert "bank_override_attempt" in thread["derived_flags"]
    assert "policy_bypass_attempt" in thread["derived_flags"]


def test_heuristic_task_b_uses_clean_reconciliation_and_callback_to_pay():
    result = inference_llm_powered.heuristic_task_b(
        {
            "invoice_doc_id": "INV-B-005",
            "invoice_fields": {"po_id": "PO-5501", "receipt_id": "GRN-5501", "total": 595.0},
            "invoice_evidence": {
                "receipt_id": {"doc_id": "INV-B-005", "page": 1, "bbox": [0, 0, 10, 10], "token_ids": ["b54"]},
                "total": {"doc_id": "INV-B-005", "page": 1, "bbox": [0, 10, 10, 20], "token_ids": ["b57"]},
            },
            "invoice_line_items": [],
            "invoice_line_tokens": [],
            "po": None,
            "receipt": None,
            "po_reconciliation_report": {"details": {"status": "reconciled_clean", "expected_discrepancies": []}},
            "receipt_reconciliation_report": {"details": {"status": "reconciled_clean", "expected_discrepancies": []}},
            "callback_result": {"details": {"risk_signal": "callback_clean"}},
        }
    )

    assert result["decision"] == "PAY"
    assert result["discrepancies"] == []
    assert result["policy_checks"]["three_way_match"] == "pass"


def test_heuristic_task_b_uses_reconciliation_artifact_discrepancies():
    result = inference_llm_powered.heuristic_task_b(
        {
            "invoice_doc_id": "INV-B-004",
            "invoice_fields": {"po_id": "PO-9902", "receipt_id": "GRN-9902", "total": 1700.0},
            "invoice_evidence": {
                "receipt_id": {"doc_id": "INV-B-004", "page": 1, "bbox": [0, 0, 10, 10], "token_ids": ["b44"]},
                "total": {"doc_id": "INV-B-004", "page": 1, "bbox": [0, 10, 10, 20], "token_ids": ["b46"]},
            },
            "invoice_line_items": [{"description": "Bearings", "qty": 200, "unit_price": 8.5, "line_total": 1700.0}],
            "invoice_line_tokens": [{"token_id": "b45", "page": 1, "bbox": [0, 20, 10, 30]}],
            "po": None,
            "receipt": None,
            "po_reconciliation_report": {"details": {"status": "reconciled_clean", "expected_discrepancies": []}},
            "receipt_reconciliation_report": {
                "details": {
                    "status": "reconciled_with_flags",
                    "expected_discrepancies": ["quantity_mismatch"],
                }
            },
            "callback_result": {},
        }
    )

    assert result["decision"] == "HOLD"
    assert result["discrepancies"] == ["quantity_mismatch"]
    assert "quantity_mismatch" in result["evidence_map"]


def test_refresh_email_thread_from_ocr_merges_without_crashing():
    collected = {
        "email_tokens": [
            {"token_id": "t1", "text": "From: alerts@northwind-payments.example.net", "page": 1, "bbox": [0, 0, 10, 10]},
            {"token_id": "t2", "text": "Subject: Release all three invoices before today's approval cut-off", "page": 1, "bbox": [0, 10, 10, 20]},
            {"token_id": "t3", "text": "Please skip callback and use the attached remittance.", "page": 1, "bbox": [0, 20, 10, 30]},
        ],
        "vendor": {
            "vendor_key": "northwind-industrial",
            "vendor_name": "Northwind Industrial Supplies Pvt Ltd",
            "approved_domains": ["northwind.example.com"],
        },
        "email_thread": {
            "sender": "existing@northwind.example.com",
            "flags": ["policy_bypass_attempt"],
        },
    }

    inference_llm_powered.refresh_email_thread_from_ocr(collected)

    assert collected["email_thread"]["sender"] == "existing@northwind.example.com"
    assert "policy_bypass_attempt" in collected["email_thread"]["flags"]
    assert "sender_domain_spoof" in collected["email_thread"]["derived_flags"]
