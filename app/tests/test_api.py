"""API tests for the FastAPI service.

The agent is monkeypatched so these tests stay fast and make no AWS calls. They
verify the HTTP contract: /ping is healthy and /invocations validates input and
returns the agent's reply.
"""

from fastapi.testclient import TestClient

import app.main as main
from app.main import app

client = TestClient(app)


def test_ping_is_healthy():
    response = client.get("/ping")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "model_id" in body


def test_invocations_returns_agent_reply(monkeypatch):
    def fake_run_agent(message: str):
        assert message == "Albury to Wagga?"
        return {
            "reply": "About 441 a day.",
            "stop_reason": "end_turn",
            "tool_calls": ["estimate_demand"],
        }

    monkeypatch.setattr(main, "run_agent", fake_run_agent)

    response = client.post("/invocations", json={"message": "Albury to Wagga?"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "About 441 a day."
    assert body["tool_calls"] == ["estimate_demand"]


def test_invocations_rejects_empty_message():
    response = client.post("/invocations", json={"message": ""})
    assert response.status_code == 422  # pydantic validation error
