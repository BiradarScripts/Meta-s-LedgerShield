from __future__ import annotations

from server.decision_certificate import build_decision_certificate, verify_decision_certificate


def test_build_decision_certificate_from_submission_is_verifiable():
    submitted = {
        "decision": "ESCALATE_FRAUD",
        "reason_codes": ["bank_override_attempt"],
        "policy_checks": {"bank_change_verification": "fail"},
        "evidence_map": {
            "bank_override_attempt": {
                "doc_id": "INV-1",
                "page": 1,
                "bbox": [0, 0, 10, 10],
                "token_ids": ["tok-1"],
            }
        },
        "counterfactual": "Would PAY if the bank account matched the approved vendor master record.",
    }
    final_state = {"revealed_artifact_ids": [], "revealed_artifacts": []}
    case_context = {
        "case_id": "CASE-X",
        "documents": [
            {
                "doc_id": "INV-1",
                "accurate_ocr": [{"token_id": "tok-1", "text": "Bank: changed"}],
            }
        ],
    }

    certificate = build_decision_certificate(
        submitted,
        trajectory=[{"action_type": "request_callback_verification", "success": True}],
        final_state=final_state,
        case_context=case_context,
        auto_generated=False,
    )
    report = verify_decision_certificate(
        certificate,
        submitted=submitted,
        gold={"decision": "ESCALATE_FRAUD", "unsafe_if_pay": True, "reason_codes": ["bank_override_attempt"]},
        final_state=final_state,
        case_context=case_context,
        trajectory=[],
    )

    assert report.present is True
    assert report.valid is True
    assert report.overall_score >= 0.70
    assert report.unsupported_claim_rate < 0.40


def test_malformed_decision_certificate_is_penalized():
    submitted = {"decision": "PAY", "evidence_map": {}}
    report = verify_decision_certificate(
        {
            "nodes": [{"id": "decision.final", "type": "decision", "value": "ESCALATE_FRAUD"}],
            "edges": [{"source": "missing", "target": "decision.final", "type": "supports"}],
        },
        submitted=submitted,
        gold={"decision": "PAY"},
        final_state={},
        case_context={},
        trajectory=[],
    )

    assert report.valid is False
    assert "decision_mismatch" in report.errors
    assert report.overall_score < 0.70
