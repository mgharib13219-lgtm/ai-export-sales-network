from types import SimpleNamespace

from app import main


def test_integration_status_reports_missing_live_providers_without_secrets(monkeypatch):
    monkeypatch.setattr(main, "settings", SimpleNamespace(
        search_provider="none",
        search_api_key="",
        ai_provider="none",
        ai_api_key="",
        email_provider="none",
        email_api_key="",
    ))

    result = main.integration_status()

    assert result["status"] == "action_required"
    assert result["search"]["status"] == "provider_not_configured"
    assert result["search"]["configured"] is False
    assert result["ai"]["status"] == "not_configured"
    assert result["email"]["status"] == "draft_only"
    assert result["secrets_exposed"] is False
    assert "SEARCH_API_KEY" in result["search"]["next_action"]


def test_integration_status_reports_configured_search_without_returning_key(monkeypatch):
    monkeypatch.setattr(main, "settings", SimpleNamespace(
        search_provider="serpapi",
        search_api_key="test-secret-value",
        ai_provider="openai",
        ai_api_key="test-ai-secret",
        email_provider="none",
        email_api_key="",
    ))

    result = main.integration_status()

    assert result["status"] == "ready"
    assert result["search"]["configured"] is True
    assert result["ai"]["configured"] is True
    assert "test-secret-value" not in str(result)
    assert "test-ai-secret" not in str(result)
