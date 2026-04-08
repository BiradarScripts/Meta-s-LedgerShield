from __future__ import annotations

from task_d_guardrails import sanitize_task_d_submission, validate_task_d_submission


def _benign_collected() -> dict:
    return {
        "invoice_records": [
            {
                "fields": {
                    "invoice_number": "BLP-8891-MAY",
                    "total": 8850.0,
                },
                "evidence": {
                    "invoice_number": {
                        "doc_id": "INV-D-002",
                        "page": 1,
                        "bbox": [10, 30, 170, 40],
                        "token_ids": ["d22"],
                    },
                    "bank_account": {
                        "doc_id": "INV-D-002",
                        "page": 1,
                        "bbox": [10, 110, 170, 120],
                        "token_ids": ["d26"],
                    },
                },
            }
        ],
        "email_evidence": {
            "from_header": {
                "doc_id": "THR-130",
                "page": 1,
                "bbox": [10, 10, 220, 20],
                "token_ids": ["ed21"],
            },
            "subject_header": {
                "doc_id": "THR-130",
                "page": 1,
                "bbox": [10, 30, 320, 40],
                "token_ids": ["ed22"],
            },
        },
        "email_thread": {
            "sender_profile": {"domain_alignment": "match"},
            "request_signals": {
                "bank_change_language": False,
                "callback_discouraged": False,
                "policy_override_language": False,
                "urgency_language": False,
            },
        },
        "ledger_search": {"exact_duplicate_count": 0},
        "ledger_hits": [],
        "bank_compares": [{"matched": True}],
        "vendor_history": [],
    }


def _risky_collected() -> dict:
    return {
        "invoice_records": [
            {
                "fields": {
                    "invoice_number": "INV-2050-A",
                    "total": 1999.0,
                },
                "evidence": {
                    "invoice_number": {
                        "doc_id": "INV-D-003A",
                        "page": 1,
                        "bbox": [10, 30, 160, 40],
                        "token_ids": ["d32"],
                    },
                    "bank_account": {
                        "doc_id": "INV-D-003A",
                        "page": 1,
                        "bbox": [10, 110, 175, 120],
                        "token_ids": ["d36"],
                    },
                },
            },
            {
                "fields": {
                    "invoice_number": "INV-2050-B",
                    "total": 1985.0,
                },
                "evidence": {
                    "invoice_number": {
                        "doc_id": "INV-D-003B",
                        "page": 1,
                        "bbox": [10, 30, 160, 40],
                        "token_ids": ["d42"],
                    },
                    "bank_account": {
                        "doc_id": "INV-D-003B",
                        "page": 1,
                        "bbox": [10, 110, 175, 120],
                        "token_ids": ["d46"],
                    },
                },
            },
        ],
        "email_evidence": {
            "from_header": {
                "doc_id": "THR-140",
                "page": 1,
                "bbox": [10, 10, 265, 20],
                "token_ids": ["ed31"],
            },
            "subject_header": {
                "doc_id": "THR-140",
                "page": 1,
                "bbox": [10, 30, 395, 40],
                "token_ids": ["ed32"],
            },
            "approval_threshold_evasion": {
                "doc_id": "THR-140",
                "page": 1,
                "bbox": [10, 70, 415, 80],
                "token_ids": ["ed34"],
            },
            "policy_bypass_attempt": {
                "doc_id": "THR-140",
                "page": 1,
                "bbox": [10, 90, 300, 100],
                "token_ids": ["ed35"],
            },
        },
        "email_thread": {
            "sender_profile": {"domain_alignment": "mismatch"},
            "request_signals": {
                "bank_change_language": True,
                "callback_discouraged": True,
                "policy_override_language": False,
                "urgency_language": True,
            },
        },
        "ledger_search": {"exact_duplicate_count": 2},
        "ledger_hits": [{"ledger_id": "LED-5"}],
        "bank_compares": [{"matched": False}, {"matched": False}],
        "vendor_history": [],
    }


def test_validate_task_d_submission_reverts_unfounded_escalation():
    validated = validate_task_d_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.95,
            "reason_codes": ["sender_domain_spoof"],
            "policy_checks": {
                "three_way_match": "pass",
                "bank_change_verification": "fail",
                "duplicate_check": "pass",
                "approval_threshold_check": "pass",
            },
            "evidence_map": {
                "sender_domain_spoof": {
                    "doc_id": "THR-130",
                    "page": 1,
                    "bbox": [10, 10, 220, 20],
                    "token_ids": ["ed21"],
                }
            },
            "counterfactual": "Would PAY if the sender domain matched vendor records.",
        },
        _benign_collected(),
    )

    assert validated["decision"] == "PAY"
    assert validated["reason_codes"] == []
    assert all(value == "pass" for value in validated["policy_checks"].values())


def test_validate_task_d_submission_repairs_missing_reasons_and_evidence():
    validated = validate_task_d_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.99,
            "reason_codes": [],
            "policy_checks": {
                "three_way_match": "pass",
                "bank_change_verification": "pass",
                "duplicate_check": "pass",
                "approval_threshold_check": "pass",
            },
            "evidence_map": {},
            "counterfactual": "",
        },
        _risky_collected(),
    )

    assert validated["decision"] == "ESCALATE_FRAUD"
    assert set(validated["reason_codes"]) == {
        "approval_threshold_evasion",
        "bank_override_attempt",
        "duplicate_near_match",
        "policy_bypass_attempt",
        "sender_domain_spoof",
    }
    assert set(validated["evidence_map"]) == {
        "approval_threshold_evasion",
        "bank_override_attempt",
        "duplicate_near_match",
        "policy_bypass_attempt",
        "sender_domain_spoof",
    }
    assert validated["policy_checks"]["bank_change_verification"] == "fail"
    assert validated["policy_checks"]["duplicate_check"] == "fail"
    assert validated["policy_checks"]["approval_threshold_check"] == "fail"


def test_sanitize_task_d_submission_preserves_partial_reasoning_for_benchmarking():
    sanitized = sanitize_task_d_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.91,
            "reason_codes": ["bank_override_attempt"],
            "policy_checks": {
                "three_way_match": "pass",
                "bank_change_verification": "fail",
            },
            "evidence_map": {
                "bank_override_attempt": {
                    "doc_id": "INV-D-003A",
                    "page": 1,
                    "bbox": [10, 110, 175, 120],
                    "token_ids": ["d36"],
                }
            },
            "counterfactual": "Would PAY if the bank matched vendor master and no fraud indicators remained.",
        },
        _risky_collected(),
    )

    assert sanitized["decision"] == "ESCALATE_FRAUD"
    assert sanitized["reason_codes"] == ["bank_override_attempt"]
    assert sanitized["policy_checks"] == {
        "three_way_match": "pass",
        "bank_change_verification": "fail",
    }
    assert set(sanitized["evidence_map"]) == {"bank_override_attempt"}
    assert sanitized["confidence"] == 0.91


def test_sanitize_task_d_submission_backfills_grounded_evidence_for_chosen_reasons():
    sanitized = sanitize_task_d_submission(
        {
            "decision": "ESCALATE_FRAUD",
            "confidence": 0.91,
            "reason_codes": ["bank_override_attempt", "policy_bypass_attempt"],
            "policy_checks": {
                "three_way_match": "pass",
                "bank_change_verification": "fail",
            },
            "evidence_map": {},
            "counterfactual": "Would PAY if the bank matched vendor master and no fraud indicators remained.",
        },
        _risky_collected(),
    )

    assert sanitized["reason_codes"] == ["bank_override_attempt", "policy_bypass_attempt"]
    assert set(sanitized["evidence_map"]) == {"bank_override_attempt", "policy_bypass_attempt"}
