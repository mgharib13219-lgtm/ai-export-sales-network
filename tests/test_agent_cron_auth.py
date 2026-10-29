from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


def test_agent_cron_requires_configured_token(monkeypatch):
    monkeypatch.setattr("app.main.settings", SimpleNamespace(agent_cron_token=""))
    response = TestClient(app).post("/agent/cron/run")
    assert response.status_code == 401


def test_agent_cron_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr("app.main.settings", SimpleNamespace(agent_cron_token="test-secret"))
    response = TestClient(app).post(
        "/agent/cron/run",
        headers={"X-Agent-Cron-Token": "wrong-secret"},
    )
    assert response.status_code == 401


def test_agent_cron_accepts_valid_token_without_running_if_idle(monkeypatch):
    monkeypatch.setattr("app.main.settings", SimpleNamespace(agent_cron_token="test-secret"))
    monkeypatch.setattr("app.main.list_due_agent_profiles", lambda limit=3: [])
    response = TestClient(app).post(
        "/agent/cron/run",
        headers={"X-Agent-Cron-Token": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "idle"
