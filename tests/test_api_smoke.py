from __future__ import annotations

from fastapi.testclient import TestClient

from envs.ledgershield_env.server.app import app


client = TestClient(app)


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


def test_state_endpoint():
    client.post("/reset", json={"case_id": "CASE-D-001"})
    response = client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "CASE-D-001"
    assert "gold" not in str(data).lower()


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
    assert data["observation"]["last_tool_result"]["tool_name"] == "ocr"
    assert data["done"] is False


def test_submit_decision_endpoint():
    client.post("/reset", json={"case_id": "CASE-D-001"})
    response = client.post(
        "/step",
        json={
            "action_type": "submit_decision",
            "payload": {
                "decision": "ESCALATE_FRAUD",
                "reason_codes": [
                    "bank_override_attempt",
                    "sender_domain_spoof",
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
                        "doc_id": "EM-D-001",
                        "page": 1,
                        "bbox": [10, 10, 250, 20],
                        "token_ids": ["ed1"],
                    },
                    "duplicate_near_match": {
                        "doc_id": "INV-D-001",
                        "page": 1,
                        "bbox": [10, 30, 150, 40],
                        "token_ids": ["d2"],
                    },
                },
                "counterfactual": "Would PAY if bank account and sender domain matched approved records.",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["done"] is True
    assert data["observation"]["last_tool_result"]["score"] > 0.90