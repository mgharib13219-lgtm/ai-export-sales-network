from types import SimpleNamespace

import app.providers as providers


def test_ensemble_merge_uses_conservative_score_and_combines_risks():
    ai = providers.AIProvider()
    result = ai._merge("buyer_verification", [
        {"provider": "openai", "status": "ok", "parsed": {
            "company_name": "Example Import GmbH", "score": 92,
            "risk_flags": ["domain_mismatch"], "evidence": ["website contact page"]
        }},
        {"provider": "gemini", "status": "ok", "parsed": {
            "company_name": "Example Import GmbH", "score": 48,
            "risk_flags": ["no_import_evidence"], "evidence": ["public company profile"]
        }},
    ])
    assert result["status"] == "ok"
    assert result["parsed"]["score"] == 66
    assert set(result["parsed"]["risk_flags"]) == {"domain_mismatch", "no_import_evidence"}
    assert result["parsed"]["_ensemble"]["provider_count"] == 2
    assert result["parsed"]["_ensemble"]["agreement"] == "partial_review_required"


def test_ensemble_merge_fails_closed_if_no_model_returns_json():
    result = providers.AIProvider()._merge("buyer_match", [
        {"provider": "openai", "status": "invalid_json", "parsed": None},
        {"provider": "gemini", "status": "provider_error", "parsed": None},
    ])
    assert result["status"] == "error"
    assert "No configured AI provider" in result["error"]


def test_ensemble_only_uses_providers_with_configured_keys(monkeypatch):
    monkeypatch.setattr(providers, "settings", SimpleNamespace(
        ai_provider="ensemble", ai_api_key="configured-a",
        anthropic_api_key="", gemini_api_key="configured-b",
    ))
    configured = providers.AIProvider()._configured()
    assert [name for name, _ in configured] == ["openai", "gemini"]


def test_single_provider_mode_does_not_call_other_provider(monkeypatch):
    monkeypatch.setattr(providers, "settings", SimpleNamespace(
        ai_provider="openai", ai_api_key="configured-a",
        anthropic_api_key="configured-b", gemini_api_key="configured-c",
    ))
    configured = providers.AIProvider()._configured()
    assert [name for name, _ in configured] == ["openai"]
