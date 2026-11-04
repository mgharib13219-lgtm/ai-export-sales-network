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
    assert result["document_evidence"]["authenticity_verified"] is False
    assert result["deal_packs"][0]["status"] == "blocked_pending_compliance_review"


def test_compliance_block_stops_buyer_discovery(monkeypatch):
    import agents.orchestrator as module

    def should_not_run(*args, **kwargs):
        raise AssertionError("buyer discovery must not run after an explicit compliance block")

    monkeypatch.setattr(module.MarketHunter, "run", should_not_run)
    monkeypatch.setattr(module.BuyerHunter, "run", should_not_run)

    result = module.Orchestrator().run({
        "name": "Controlled product",
        "origin": "Country A",
        "hs_code": "1234",
        "target_countries": ["Country B"],
        "sanctions_hit": True,
    }, "blocked-run")

    assert result["status"] == "blocked_pending_compliance_review"
    assert result["matches"] == []
    assert result["lead_ids"] == []
    assert result["compliance_review"]["legal_clearance"] is False
    assert result["document_evidence"]["human_review_required"] is True
    assert result["deal_packs"] == []
    assert result["quality_audit"]["status"] == "NEEDS_REVIEW"


def test_normal_pipeline_attaches_compliance_hold_and_specialist_outputs(monkeypatch):
    import agents.orchestrator as module

    monkeypatch.setattr(module.MarketHunter, "run", lambda self, product: [{"country": "Germany"}])
    monkeypatch.setattr(module.BuyerHunter, "run", lambda self, product, markets: [
        {"market": "Germany", "status": "candidate", "title": "Buyer",
         "url": "https://buyer.example.org", "domain": "buyer.example.org"}
    ])
    monkeypatch.setattr(module.VerificationAgent, "run", lambda self, buyers: [
        {**buyers[0], "verification": {"status": "review_required", "score": 55,
                                      "decision": "human_review_required", "identity_verified": False}}
    ])
    monkeypatch.setattr(module.MatchAgent, "run", lambda self, product, buyers: buyers)
    monkeypatch.setattr(module.OutreachAgent, "run", lambda self, product, matches: [])
    monkeypatch.setattr(module.DealIntelligence, "run", lambda self, product, matches: {"status": "pending"})
    monkeypatch.setattr(module, "upsert_lead", lambda match: 23)

    result = module.Orchestrator().run({"name": "Olive oil"}, "normal-run")

    assert result["compliance_review"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["matches"][0]["compliance_clearance"] is False
    assert result["matches"][0]["human_compliance_review_required"] is True
    assert result["supplier_onboarding"]["identity_verified"] is False
    assert result["catalogue_draft"]["status"] == "draft_only"
    assert result["document_evidence"]["human_review_required"] is True
    assert result["deal_packs"][0]["status"] == "blocked_pending_compliance_review"
    assert result["quality_audit"]["human_review_required"] is True
