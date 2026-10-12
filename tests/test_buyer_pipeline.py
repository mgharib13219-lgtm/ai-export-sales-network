from agents.verifier import VerificationAgent
from agents.matcher import MatchAgent


def test_verification_without_url():
    result = VerificationAgent().run([{"market": "Turkey", "title": "x"}])[0]
    assert result["verification"]["score"] == 0
    assert "no_url" in result["verification"]["risk_flags"]
    assert result["verification"]["status"] == "pending"
    assert result["verification"]["identity_verified"] is False


def test_match_uses_verification_score(monkeypatch):
    class AI:
        def analyze(self, *args, **kwargs):
            return {"status": "ok", "parsed": {"fit_score": 80, "reasons": ["product fit"]}}

    monkeypatch.setattr("agents.matcher.ai_provider", AI())
    result = MatchAgent().run({}, [{"verification": {"score": 90}}])[0]
    assert result["match_score"] == 86


def test_buyer_hunter_reports_missing_search_provider(monkeypatch):
    from types import SimpleNamespace
    import agents.buyer_hunter as module

    monkeypatch.setattr(module, "settings", SimpleNamespace(search_provider="none", search_api_key=""))
    result = module.BuyerHunter().run({"name": "Dates"}, [{"country": "Oman"}])
    assert len(result) == 1
    assert result[0]["status"] == "provider_not_configured"
    assert result[0]["queries_attempted"] == 4


def test_buyer_hunter_surfaces_provider_errors(monkeypatch):
    from types import SimpleNamespace
    import agents.buyer_hunter as module

    class BrokenSearch:
        def search_buyers(self, query, country):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(module, "settings", SimpleNamespace(search_provider="serpapi", search_api_key="configured"))
    monkeypatch.setattr(module, "search_provider", BrokenSearch())
    result = module.BuyerHunter().run({"name": "Dates"}, [{"country": "Oman"}])
    assert result[0]["status"] == "search_provider_error"
    assert result[0]["query_errors"] == 4


def test_verifier_marks_ai_unavailable_and_records_public_evidence(monkeypatch):
    import agents.verifier as module

    monkeypatch.setattr(module, "contact_extractor", type("Extractor", (), {
        "extract": lambda self, url: {
            "website": {"reachable": True, "final_url": url, "status_code": 200},
            "contact": {"emails": ["sales@example.org"], "phones": [], "contact_pages": [url + "/contact"]},
            "buyer_signals": ["importer"],
        }
    })())
    monkeypatch.setattr(module, "ai_provider", type("AI", (), {
        "analyze": lambda self, task, payload: {"status": "not_configured", "task": task}
    })())

    result = module.VerificationAgent().run([{"title": "Example Importer", "url": "https://example.org"}])[0]
    verification = result["verification"]
    assert verification["status"] == "ai_review_unavailable"
    assert verification["identity_verified"] is False
    assert verification["decision"] == "human_review_required"
    assert verification["evidence_sources"][0]["type"] == "public_website"
    assert verification["contact_evidence"]["email_count"] == 1


def test_verifier_never_calls_automated_review_identity_proof(monkeypatch):
    import agents.verifier as module

    monkeypatch.setattr(module, "contact_extractor", type("Extractor", (), {
        "extract": lambda self, url: {
            "website": {"reachable": True, "final_url": url, "status_code": 200},
            "contact": {"emails": ["sales@example.org"], "phones": ["+1234567890"], "contact_pages": [url + "/contact"]},
            "buyer_signals": ["importer", "wholesale"],
        }
    })())
    monkeypatch.setattr(module, "ai_provider", type("AI", (), {
        "analyze": lambda self, task, payload: {
            "status": "ok",
            "parsed": {"company_name": "Example Importer", "buyer_type": "importer", "score": 90,
                       "risk_flags": [], "evidence": ["website says importer"]},
        }
    })())

    result = module.VerificationAgent().run([{"title": "Example Importer", "url": "https://example.org"}])[0]
    verification = result["verification"]
    assert verification["status"] == "review_required"
    assert verification["identity_verified"] is False
    assert "automated_review_not_identity_proof" in verification["risk_flags"]
    assert verification["score"] == 96



def test_verifier_flags_free_email_and_domain_mismatch_without_claiming_identity(monkeypatch):
    import agents.verifier as module

    monkeypatch.setattr(module, "contact_extractor", type("Extractor", (), {
        "extract": lambda self, url: {
            "website": {"reachable": True, "final_url": url, "status_code": 200},
            "contact": {
                "emails": ["sales@gmail.com", "orders@unrelated-example.net"],
                "phones": [], "contact_pages": [],
            },
            "buyer_signals": ["importer"],
        }
    })())
    monkeypatch.setattr(module, "ai_provider", type("AI", (), {
        "analyze": lambda self, task, payload: {
            "status": "ok",
            "parsed": {"company_name": "Example Buyer", "score": 75, "risk_flags": [], "evidence": []},
        }
    })())

    result = module.VerificationAgent().run([
        {"title": "Example Buyer", "url": "https://buyer.example.org"}
    ])[0]["verification"]

    assert "free_email_provider" in result["risk_flags"]
    assert "email_domain_mismatch" in result["risk_flags"]
    assert result["identity_verified"] is False
    assert result["decision"] == "human_review_required"


def test_verifier_does_not_flag_matching_company_email_domain(monkeypatch):
    import agents.verifier as module

    agent = module.VerificationAgent()
    assert agent._contact_risk_flags({
        "url": "https://buyer.example.org",
        "contact": {"emails": ["sales@buyer.example.org", "info@example.org"]},
    }) == []
