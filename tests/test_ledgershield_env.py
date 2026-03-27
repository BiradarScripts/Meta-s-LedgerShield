from fastapi.testclient import TestClient
from ledgershield_env.server.app import app
client = TestClient(app)

def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_reset_returns_case() -> None:
    response = client.post("/reset")
    assert response.status_code == 200
    body = response.json()
    assert "observation" in body
    assert "case_id" in body["observation"]

def test_step_ocr() -> None:
    # Use a seed to ensure deterministic testing so we know exactly which case loads
    response_reset = client.post("/reset?seed=42")
    assert response_reset.status_code == 200
    
    # Now we safely test the step function
    response = client.post(
        "/step",
        json={
            "action_type": "ocr",
            "payload": {"doc_id": "INV-A-001", "mode": "accurate"},
        },
    )
    
    assert response.status_code == 200
    body = response.json()
    assert "observation" in body
    assert "last_tool_result" in body["observation"]