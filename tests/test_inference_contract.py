from __future__ import annotations

import io
from contextlib import redirect_stdout

import inference
from server.data_loader import load_all


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


def test_log_end_clamps_stdout_score_to_open_interval():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        inference.log_end(success=False, steps=0, rewards=[], score=0.0)
        inference.log_end(success=True, steps=1, rewards=[1.0], score=1.0)

    lines = buffer.getvalue().splitlines()
    assert lines == [
        "[END] success=false steps=0 score=0.01 rewards=",
        "[END] success=true steps=1 score=0.99 rewards=1.00",
    ]


def test_log_formatting_never_emits_negative_zero():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        inference.log_step(
            step=1,
            action="lookup_po({})",
            reward=-0.0001,
            done=False,
            error=None,
        )
        inference.log_end(success=True, steps=2, rewards=[-0.0001, 0.994], score=0.994)

    lines = buffer.getvalue().splitlines()
    assert lines == [
        "[STEP] step=1 action=lookup_po({}) reward=0.00 done=false error=null",
        "[END] success=true steps=2 score=0.99 rewards=0.00,0.99",
    ]


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


def test_build_investigation_candidates_keep_receipt_lookup_for_tax_only_task_b():
    candidates = inference.build_investigation_candidates(
        "task_b",
        {
            "case_instruction": "Verify tax calculations match between invoice and PO. Report any discrepancies.",
            "invoice_fields": {"po_id": "PO-5501", "receipt_id": "GRN-5501"},
        },
        vendor_key="",
        po_id="PO-5501",
        receipt_id="GRN-5501",
        invoice_total=595.0,
        invoice_number="EC-5501",
        proposed_bank_account="",
        email_doc_id="",
        executed_signatures=set(),
    )

    assert [candidate.action_type for candidate in candidates] == ["lookup_policy", "lookup_po", "lookup_receipt"]


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


def test_merge_submission_override_handles_non_empty_collections():
    base = {
        "decision": "PAY",
        "reason_codes": [],
        "policy_checks": {
            "three_way_match": "pass",
            "bank_change_verification": "pass",
            "duplicate_check": "pass",
            "approval_threshold_check": "pass",
        },
    }
    override = {
        "reason_codes": ["sender_domain_spoof"],
        "evidence_map": {
            "sender_domain_spoof": {
                "doc_id": "THR-130",
                "page": 1,
                "bbox": [10, 10, 220, 20],
                "token_ids": ["ed21"],
            }
        },
    }

    merged = inference.merge_submission_override(base, override)

    assert merged["reason_codes"] == ["sender_domain_spoof"]
    assert "sender_domain_spoof" in merged["evidence_map"]


def test_run_local_baseline_blocks_unfounded_task_d_escalation(monkeypatch):
    original = inference.build_final_submission

    def fake_build(task_type: str, collected: dict, model_assessment: dict) -> dict:
        if task_type != "task_d":
            return original(task_type, collected, model_assessment)
        return {
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
        }

    monkeypatch.setattr(inference, "build_final_submission", fake_build)

    result = inference.run_local_baseline(["CASE-D-002"], db=load_all(), emit_logs=False)
    case = result["results"][0]

    assert case["final_decision"] == "PAY"
    assert case["score"] >= 0.8  # Lowered due to new tightened grading (Phase 2)


def test_run_local_baseline_repairs_incomplete_task_d_fraud_submission(monkeypatch):
    original = inference.build_final_submission

    def fake_build(task_type: str, collected: dict, model_assessment: dict) -> dict:
        if task_type != "task_d":
            return original(task_type, collected, model_assessment)
        return {
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
        }

    monkeypatch.setattr(inference, "build_final_submission", fake_build)

    result = inference.run_local_baseline(["CASE-D-003"], db=load_all(), emit_logs=False)
    case = result["results"][0]

    assert case["final_decision"] == "ESCALATE_FRAUD"
    assert case["score"] >= 0.85  # Lowered due to new tightened grading (Phase 2)


def test_build_task_e_submission_detects_vendor_takeover_patterns():
    collected = {
        "invoice_records": [
            {
                "doc_id": "INV-E-SC-001",
                "fields": {"bank_account": "DE00COMPROMISED999", "total": 49500.0},
                "evidence": {
                    "bank_account": {
                        "doc_id": "INV-E-SC-001",
                        "page": 1,
                        "bbox": [10, 70, 190, 80],
                        "token_ids": ["esc4"],
                    }
                },
            },
            {
                "doc_id": "INV-E-SC-002",
                "fields": {"bank_account": "DE00COMPROMISED999", "total": 49000.0},
                "evidence": {
                    "bank_account": {
                        "doc_id": "INV-E-SC-002",
                        "page": 1,
                        "bbox": [10, 70, 190, 80],
                        "token_ids": ["esc8"],
                    }
                },
            },
        ],
        "email_thread": {
            "sender_profile": {"domain_alignment": "mismatch"},
            "request_signals": {
                "bank_change_language": True,
                "callback_discouraged": True,
                "policy_override_language": True,
                "urgency_language": False,
            },
        },
        "email_evidence": {
            "from_header": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 10, 280, 20],
                "token_ids": ["eesc1"],
            },
            "policy_bypass_attempt": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 70, 400, 80],
                "token_ids": ["eesc4"],
            },
        },
        "bank_compares": [{"matched": False}],
        "ledger_hits": [],
        "vendor_history": [],
        "callback_result": {"details": {"risk_signal": "callback_suspicious_confirm"}},
    }

    submission = inference.build_task_e_submission(collected, {})

    assert submission["decision"] == "ESCALATE_FRAUD"
    assert "vendor_account_takeover_suspected" in submission["reason_codes"]
    assert "sender_domain_spoof" in submission["reason_codes"]
    assert "bank_override_attempt" in submission["reason_codes"]
    assert "shared_bank_account" in submission["campaign_signals"]


def test_sanitize_task_e_submission_recovers_grounded_refs_and_policy():
    collected = {
        "invoice_records": [
            {
                "doc_id": "INV-E-SC-001",
                "fields": {"bank_account": "DE00COMPROMISED999", "total": 49500.0},
                "evidence": {
                    "bank_account": {
                        "doc_id": "INV-E-SC-001",
                        "page": 1,
                        "bbox": [10, 70, 190, 80],
                        "token_ids": ["esc4"],
                    }
                },
            },
            {
                "doc_id": "INV-E-SC-002",
                "fields": {"bank_account": "DE00COMPROMISED999", "total": 49000.0},
                "evidence": {
                    "bank_account": {
                        "doc_id": "INV-E-SC-002",
                        "page": 1,
                        "bbox": [10, 70, 190, 80],
                        "token_ids": ["esc8"],
                    }
                },
            },
        ],
        "email_thread": {
            "sender_profile": {"domain_alignment": "mismatch"},
            "request_signals": {
                "bank_change_language": True,
                "callback_discouraged": True,
                "policy_override_language": True,
                "urgency_language": False,
            },
        },
        "email_evidence": {
            "from_header": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 10, 280, 20],
                "token_ids": ["eesc1"],
            },
            "subject_header": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 30, 340, 40],
                "token_ids": ["eesc2"],
            },
            "approval_threshold_evasion": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 70, 420, 80],
                "token_ids": ["eesc4"],
            },
            "policy_bypass_attempt": {
                "doc_id": "THR-E-SC-001",
                "page": 1,
                "bbox": [10, 90, 395, 100],
                "token_ids": ["eesc5"],
            },
        },
        "bank_compares": [{"matched": False}],
        "ledger_hits": [],
        "vendor_history": [],
        "callback_result": {"details": {"risk_signal": "callback_suspicious_confirm"}},
    }
    grounded = inference.build_task_e_submission(collected, {})
    candidate = {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.91,
        "reason_codes": list(grounded["reason_codes"]),
        "campaign_signals": list(grounded["campaign_signals"]),
        "cross_invoice_links": list(grounded["cross_invoice_links"]),
        "policy_checks": {
            "three_way_match": "pass",
            "bank_change_verification": "pass",
            "duplicate_check": "pass",
            "approval_threshold_check": "pass",
        },
        "evidence_map": {
            "bank_override_attempt": {"doc_id": "INV-E-SC-001"},
            "sender_domain_spoof": {"doc_id": "THR-E-SC-001"},
            "approval_threshold_evasion": {"doc_id": "THR-E-SC-001"},
            "policy_bypass_attempt": {"doc_id": "THR-E-SC-001"},
            "shared_bank_account": {"doc_id": "INV-E-SC-002"},
            "coordinated_timing": {"doc_id": "INV-E-SC-001"},
        },
        "counterfactual": "Would PAY if the invoices had distinct approved bank details and no coordinated campaign signals.",
    }

    sanitized = inference.sanitize_task_e_submission(candidate, collected)

    assert sanitized["policy_checks"] == grounded["policy_checks"]
    assert sanitized["evidence_map"] == grounded["evidence_map"]
