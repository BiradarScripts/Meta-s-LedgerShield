from __future__ import annotations

from server.compliance_engine import ComplianceResult
from server.data_loader import load_all
from server.environment import LedgerShieldEnvironment
from server.grading import DEGENERATE_EVIDENCE_CAP, evidence_score, score_submission
from server.outcome_simulator import simulate_outcome
from server.world_state import system_state_snapshot


def test_evidence_score_caps_empty_submission_at_degenerate_limit():
    gold_map = {
        "invoice_total": {
            "doc_id": "INV-123",
            "page": 1,
            "bbox": [10, 20, 120, 60],
            "token_ids": [7, 8, 9],
        }
    }

    assert evidence_score({}, gold_map) == DEGENERATE_EVIDENCE_CAP


def test_task_e_requires_multiple_exact_cross_invoice_links_for_passing_score():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-E-001")
    gold = env.current_case["gold"]

    submission = {
        "decision": gold["decision"],
        "confidence": 0.98,
        "reason_codes": list(gold["reason_codes"]),
        "campaign_signals": list(gold["campaign_signals"]),
        "cross_invoice_links": ["INV-E-001"],
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": "Would PAY if the invoices looked legitimate.",
    }
    trajectory = [
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-E-001"}, "success": True},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "lookup_policy", "payload": {}, "success": True},
        {"action_type": "compare_bank_account", "payload": {"vendor_key": "northwind-industrial"}, "success": True},
        {"action_type": "request_callback_verification", "payload": {}, "success": True},
        {"action_type": "route_to_security", "payload": {}, "success": True},
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
        trajectory=trajectory,
        outcome=outcome,
        final_state=system_state_snapshot(env.state, env._hidden_world),
        case_context=env.current_case,
        compliance_result=ComplianceResult(
            overall_compliant=True,
            controls_evaluated=1,
            controls_passed=1,
            controls_failed=0,
            compliance_score=1.0,
        ),
        currency_validation={"score": 1.0, "applicable": False},
    )

    assert score <= 0.84, breakdown
    assert breakdown["cross_invoice_link_matches"] == 1.0
    assert breakdown["counterfactual_doc_refs"] == 0.0


def test_task_a_currency_validation_penalizes_invalid_bank_format():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-A-003")
    gold = env.current_case["gold"]

    valid_submission = {
        "decision": "NEEDS_REVIEW",
        "confidence": 0.95,
        "extracted_fields": dict(gold["fields"]),
        "line_items": list(gold["line_items"]),
        "evidence_map": {},
    }
    invalid_submission = {
        **valid_submission,
        "extracted_fields": {**gold["fields"], "bank_account": "CH00INVALID"},
    }
    compliant = ComplianceResult(
        overall_compliant=True,
        controls_evaluated=1,
        controls_passed=1,
        controls_failed=0,
        compliance_score=1.0,
    )

    valid_score, valid_breakdown = score_submission(
        "task_a",
        valid_submission,
        gold,
        case_context=env.current_case,
        compliance_result=compliant,
    )
    invalid_score, invalid_breakdown = score_submission(
        "task_a",
        invalid_submission,
        gold,
        case_context=env.current_case,
        compliance_result=compliant,
    )

    assert valid_breakdown["currency_validation_score"] == 1.0
    assert invalid_breakdown["currency_validation_score"] < 1.0
    assert invalid_score < valid_score


def test_task_d_graph_state_is_read_from_top_level_case_context():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001::variant-0"]
    gold = case["gold"]
    counterfactual = (
        "If the invoice only claims identity and the payment request did not contradict "
        "the approved bank, then I would pay after review."
    )
    submission = {
        "decision": gold["decision"],
        "confidence": 0.98,
        "reason_codes": list(gold["reason_codes"]),
        "policy_checks": dict(gold["policy_checks"]),
        "evidence_map": dict(gold["evidence_targets"]),
        "counterfactual": counterfactual,
    }
    compliant = ComplianceResult(
        overall_compliant=True,
        controls_evaluated=1,
        controls_passed=1,
        controls_failed=0,
        compliance_score=1.0,
    )

    top_level_score, top_level_breakdown = score_submission(
        "task_d",
        submission,
        gold,
        trajectory=[],
        outcome={},
        final_state={},
        case_context={"graph_state": case["graph_state"]},
        compliance_result=compliant,
        currency_validation={"score": 1.0, "applicable": False},
    )
    nested_score, nested_breakdown = score_submission(
        "task_d",
        submission,
        gold,
        trajectory=[],
        outcome={},
        final_state={},
        case_context={"case_snapshot": {"graph_state": case["graph_state"]}},
        compliance_result=compliant,
        currency_validation={"score": 1.0, "applicable": False},
    )
    plain_score, plain_breakdown = score_submission(
        "task_d",
        submission,
        gold,
        trajectory=[],
        outcome={},
        final_state={},
        case_context={},
        compliance_result=compliant,
        currency_validation={"score": 1.0, "applicable": False},
    )

    assert top_level_breakdown["counterfactual_score"] == nested_breakdown["counterfactual_score"]
    assert top_level_breakdown["counterfactual_score"] > plain_breakdown["counterfactual_score"]
    assert top_level_score == nested_score
    assert top_level_score > plain_score
