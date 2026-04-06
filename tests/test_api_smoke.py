from __future__ import annotations

"""
API smoke tests for LedgerShield.

Run:
    python -m pytest tests/test_api_smoke.py -q
"""

from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


def _run_task_d_investigation_steps() -> None:
    """
    Do a short realistic investigation before submitting task D.
    This is important because the new grader rewards trajectory quality,
    not just the final answer.
    """
    steps = [
        {
            "action_type": "inspect_email_thread",
            "payload": {"thread_id": "THR-100"},
        },
        {
            "action_type": "lookup_vendor_history",
            "payload": {"vendor_key": "northwind-industrial"},
        },
        {
            "action_type": "lookup_policy",
            "payload": {},
        },
        {
            "action_type": "compare_bank_account",
            "payload": {
                "vendor_key": "northwind-industrial",
                "proposed_bank_account": "IN99FAKE000999888",
            },
        },
        {
            "action_type": "request_callback_verification",
            "payload": {},
        },
    ]

    for step in steps:
        response = client.post("/step", json=step)
        assert response.status_code == 200, response.text


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_reset_endpoint():
    response = client.post("/reset", json={"case_id": "CASE-A-001"})
    assert response.status_code == 200

    data = response.json()
    assert data["observation"]["case_id"] == "CASE-A-001"
    assert data["done"] is False
    assert data["observation"]["task_type"] == "task_a"
    assert len(data["observation"]["visible_documents"]) >= 1
    assert "benchmark_split" not in data["observation"]["case_metadata"]


def test_state_endpoint():
    client.post("/reset", json={"case_id": "CASE-D-001"})

    response = client.get("/state")
    assert response.status_code == 200

    data = response.json()
    assert data["case_id"] == "CASE-D-001"
    assert "gold" not in str(data).lower()
    assert "hidden_risk_signals" not in data
    assert "observed_risk_signals" in data
    assert "pending_events" in data


def test_step_ocr_endpoint():
    client.post("/reset", json={"case_id": "CASE-A-001"})

    response = client.post(
        "/step",
        json={
            "action_type": "ocr",
            "payload": {"doc_id": "INV-A-001", "mode": "accurate"},
        },
    )
    assert response.status_code == 200

    data = response.json()
    last = data["observation"]["last_tool_result"]

    assert last["tool_name"] == "ocr"
    assert last["success"] is True
    assert len(last["tokens"]) > 0
    assert "reward_model" in data["info"]
    assert data["info"]["reward_model"]["terminal"] is False
    assert data["done"] is False


def test_submit_decision_endpoint():
    client.post("/reset", json={"case_id": "CASE-D-001"})
    _run_task_d_investigation_steps()

    response = client.post(
        "/step",
        json={
            "action_type": "submit_decision",
            "payload": {
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
                    "Would PAY if the sender domain matched approved vendor records "
                    "and the bank account matched vendor master."
                ),
            },
        },
    )
    assert response.status_code == 200

    data = response.json()
    result = data["observation"]["last_tool_result"]

    assert data["done"] is True
    assert result["tool_name"] == "submit_decision"
    assert result["success"] is True
    assert result["decision"] == "ESCALATE_FRAUD"
    assert result["final_score"] > 0.90
    assert data["info"]["reward_model"]["terminal"] is True


def test_clean_duplicate_screening_case_returns_no_hits():
    client.post("/reset", json={"case_id": "CASE-C-002"})

    response = client.post(
        "/step",
        json={
            "action_type": "search_ledger",
            "payload": {
                "vendor_key": "eurocaps-components",
                "invoice_number": "EC-4402-26",
                "amount": 845.0,
            },
        },
    )
    assert response.status_code == 200

    data = response.json()
    last = data["observation"]["last_tool_result"]
    assert last["tool_name"] == "search_ledger"
    assert last["count"] == 0


def test_clean_task_d_pay_submission_endpoint():
    client.post("/reset", json={"case_id": "CASE-D-002"})

    steps = [
        {"action_type": "ocr", "payload": {"doc_id": "THR-130", "mode": "accurate"}},
        {"action_type": "inspect_email_thread", "payload": {"thread_id": "THR-130"}},
        {"action_type": "lookup_vendor_history", "payload": {"vendor_key": "bluepeak-logistics"}},
        {"action_type": "lookup_policy", "payload": {}},
        {
            "action_type": "compare_bank_account",
            "payload": {
                "vendor_key": "bluepeak-logistics",
                "proposed_bank_account": "IN77BP555666777",
            },
        },
        {
            "action_type": "search_ledger",
            "payload": {
                "vendor_key": "bluepeak-logistics",
                "invoice_number": "BLP-8891-MAY",
                "amount": 8850.0,
            },
        },
    ]

    for step in steps:
        response = client.post("/step", json=step)
        assert response.status_code == 200, response.text

    response = client.post(
        "/step",
        json={
            "action_type": "submit_decision",
            "payload": {
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
        },
    )
    assert response.status_code == 200

    data = response.json()
    result = data["observation"]["last_tool_result"]
    assert data["done"] is True
    assert result["decision"] == "PAY"
    assert result["final_score"] > 0.85


def test_campaign_task_d_reset_exposes_portfolio_context():
    response = client.post("/reset", json={"case_id": "CASE-D-003"})
    assert response.status_code == 200

    data = response.json()
    observation = data["observation"]
    invoice_docs = [doc for doc in observation["visible_documents"] if doc["doc_type"] == "invoice"]

    assert len(invoice_docs) == 2
    assert observation["portfolio_context"]["linked_invoice_count"] == 2
    assert observation["portfolio_context"]["queue_pressure"] == "campaign"
