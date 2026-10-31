from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main
from app.auth import require_admin


def test_system_readiness_reports_missing_secrets_without_values(monkeypatch):
    monkeypatch.setattr(main, "settings", SimpleNamespace(
        admin_token="", database_url="", environment="production",
        ai_provider="none", ai_api_key="", anthropic_api_key="", gemini_api_key="",
        search_provider="serpapi", search_api_key="", agent_approver_token="",
        agent_cron_token="", email_provider="none", smtp_host="", smtp_user="",
        smtp_password="", app_version="test"
    ))
    app = FastAPI()
    app.include_router(main.app.router)
    app.dependency_overrides[require_admin] = lambda: True
    response = TestClient(app).get("/system/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert "configure_ADMIN_TOKEN" in body["blockers"]
    assert "production_requires_PostgreSQL" in body["blockers"]
    assert all("secret" not in str(value).lower() for value in body["checks"].values())


def test_ready_endpoint_does_not_disclose_database_exception(monkeypatch):
    import app.db as db

    def broken_connection():
        raise RuntimeError("postgres://user:password@private-host/database")

    monkeypatch.setattr(db, "_con", broken_connection)
    monkeypatch.setattr(db, "_execute", lambda *args, **kwargs: None)
    app = FastAPI()
    app.include_router(main.app.router)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert "private-host" not in response.text
    assert "password" not in response.text


def test_system_readiness_requires_admin_authentication(monkeypatch):
    import app.auth as auth

    monkeypatch.setattr(auth, "settings", SimpleNamespace(
        environment="production", admin_token="test-admin-secret"
    ))
    app = FastAPI()
    app.include_router(main.app.router)
    response = TestClient(app).get("/system/readiness")
    assert response.status_code == 401
