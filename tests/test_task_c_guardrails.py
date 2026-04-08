from __future__ import annotations

from task_c_guardrails import sanitize_task_c_submission, validate_task_c_submission


def _clean_collected() -> dict:
    return {
        "invoice_evidence": {
            "invoice_number": {
                "doc_id": "INV-C-002",
                "page": 1,
                "bbox": [10, 30, 150, 40],
                "token_ids": ["c22"],
            },
            "bank_account": {
                "doc_id": "INV-C-002",
                "page": 1,
                "bbox": [10, 70, 180, 80],
                "token_ids": ["c24"],
            },
        },
        "ledger_search": {"exact_duplicate_count": 0, "near_duplicate_count": 0},
        "ledger_hits": [],
        "bank_compare": {"matched": True},
        "bank_compares": [{"matched": True}],
    }


def _risky_collected() -> dict:
    return {
        "invoice_evidence": {
            "invoice_number": {
                "doc_id": "INV-C-001",
                "page": 1,
                "bbox": [10, 30, 150, 40],
                "token_ids": ["c2"],
            },
            "bank_account": {
                "doc_id": "INV-C-001",
                "page": 1,
                "bbox": [10, 70, 170, 80],
                "token_ids": ["c4"],
            },
        },
        "ledger_search": {"exact_duplicate_count": 2, "near_duplicate_count": 0},
        "ledger_hits": [
            {"ledger_id": "LED-131"},
            {"ledger_id": "LED-3"},
        ],
        "bank_compare": {"matched": False},
        "bank_compares": [{"matched": False}],
    }


def test_validate_task_c_submission_reverts_false_escalation_for_clean_case():
    validated = validate_task_c_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.95,
            "fraud_flags": ["bank_override_attempt"],
            "duplicate_links": ["LED-999"],
            "evidence_map": {
                "bank_override_attempt": {
                    "doc_id": "INV-C-002",
                    "page": 1,
                    "bbox": [10, 70, 180, 80],
                    "token_ids": ["c24"],
                }
            },
        },
        _clean_collected(),
    )

    assert validated["decision"] == "PAY"
    assert validated["fraud_flags"] == []
    assert validated["duplicate_links"] == []
    assert validated["evidence_map"] == {}


def test_validate_task_c_submission_repairs_partial_fraud_output():
    validated = validate_task_c_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.91,
            "fraud_flags": ["bank_override_attempt"],
            "duplicate_links": ["LED-131"],
            "evidence_map": {
                "bank_override_attempt": {
                    "doc_id": "INV-C-001",
                    "page": 1,
                    "bbox": [10, 70, 170, 80],
                    "token_ids": ["c4"],
                }
            },
        },
        _risky_collected(),
    )

    assert validated["decision"] == "ESCALATE_FRAUD"
    assert set(validated["fraud_flags"]) == {"bank_override_attempt", "duplicate_near_match"}
    assert validated["duplicate_links"] == ["LED-131", "LED-3"]
    assert set(validated["evidence_map"]) == {"bank_override_attempt", "duplicate_near_match"}
    assert validated["confidence"] >= 0.98


def test_sanitize_task_c_submission_preserves_model_miss_for_benchmarking():
    sanitized = sanitize_task_c_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.91,
            "fraud_flags": ["bank_override_attempt"],
            "duplicate_links": ["LED-131"],
            "evidence_map": {
                "bank_override_attempt": {
                    "doc_id": "INV-C-001",
                    "page": 1,
                    "bbox": [10, 70, 170, 80],
                    "token_ids": ["c4"],
                }
            },
        },
        _risky_collected(),
    )

    assert sanitized["decision"] == "ESCALATE_FRAUD"
    assert sanitized["fraud_flags"] == ["bank_override_attempt"]
    assert sanitized["duplicate_links"] == ["LED-131"]
    assert sanitized["confidence"] == 0.91
    assert set(sanitized["evidence_map"]) == {"bank_override_attempt"}


def test_sanitize_task_c_submission_backfills_grounded_evidence_for_chosen_flags():
    sanitized = sanitize_task_c_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.91,
            "fraud_flags": ["bank_override_attempt"],
            "duplicate_links": [],
            "evidence_map": {},
        },
        _risky_collected(),
    )

    assert sanitized["fraud_flags"] == ["bank_override_attempt"]
    assert set(sanitized["evidence_map"]) == {"bank_override_attempt"}
