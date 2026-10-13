def test_search_diagnostics_never_become_buyer_matches_or_crm_leads(monkeypatch):
    import agents.orchestrator as module

    monkeypatch.setattr(module.MarketHunter, "run", lambda self, product: [{"country": "Oman"}])
    monkeypatch.setattr(module.BuyerHunter, "run", lambda self, product, markets: [
        {"market": "Oman", "status": "provider_not_configured", "reason": "missing key"},
        {"market": "Oman", "status": "candidate", "title": "Real Candidate",
         "url": "https://buyer.example.org", "domain": "buyer.example.org"},
    ])
    monkeypatch.setattr(module.VerificationAgent, "run", lambda self, buyers: [
        {**buyers[0], "verification": {"status": "review_required", "score": 55}}
    ])
    monkeypatch.setattr(module.MatchAgent, "run", lambda self, product, buyers: buyers)
    monkeypatch.setattr(module.OutreachAgent, "run", lambda self, product, matches: [])
    monkeypatch.setattr(module.DealIntelligence, "run", lambda self, product, matches: {})
    monkeypatch.setattr(module, "upsert_lead", lambda match: 17)
    monkeypatch.setattr(module, "add_activity", lambda *args: None)

    result = module.Orchestrator().run({"name": "dates"}, "test-run")

    assert len(result["buyer_discovery_diagnostics"]) == 1
    assert result["buyer_discovery_diagnostics"][0]["status"] == "provider_not_configured"
    assert [buyer["title"] for buyer in result["buyers"]] == ["Real Candidate"]
    assert result["lead_ids"] == [17]
