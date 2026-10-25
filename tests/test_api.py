from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ui_is_served():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "MCP Enterprise Intelligence Agent" in response.text


def test_chat_persists_trace(monkeypatch):
    async def fake_run_research(query: str, trace_id: str | None = None):
        return {
            "route": "rag",
            "plan": {"tasks": ["rag"]},
            "answer": "Evidence-backed demo answer.",
            "sources": [{"id": "S1", "type": "document", "citation": "demo.md"}],
            "steps": [],
            "warnings": [],
        }

    monkeypatch.setattr("app.api.routes.run_research", fake_run_research)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"question": "What does the demo report say?"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "What does the demo report say?"
        trace = client.get(f"/api/traces/{payload['trace_id']}")
        assert trace.status_code == 200
        assert trace.json()["query"] == payload["query"]
        assert trace.json()["answer"] == "Evidence-backed demo answer."
