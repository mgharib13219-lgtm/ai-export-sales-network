from agents.rfq import RFQAgent

def test_rfq_draft_is_human_review_only(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.rfq.add_activity", lambda *args: calls.append(args) or 41)
    product = {
        "name": "Iranian Dates", "description": "Premium dates", "hs_code": "080410",
        "unit": "kg", "base_price": 2.5, "currency": "USD", "moq": 1000
    }
    lead = {"id": 7, "company_name": "Buyer LLC", "email": "buyer@example.com"}
    result = RFQAgent().create_draft(product, lead)
    assert result["status"] == "draft_only"
    assert result["decision"] == "human_review_required"
    assert result["activity_id"] == 41
    assert result["to"] == "buyer@example.com"
    assert calls and calls[0][1] == "rfq"

def test_rfq_requires_product_commercial_fields(monkeypatch):
    monkeypatch.setattr("agents.rfq.add_activity", lambda *args: 1)
    product = {"name": "Product", "description": "x"}
    lead = {"id": 7, "company_name": "Buyer LLC", "email": "buyer@example.com"}
    result = RFQAgent().create_draft(product, lead)
    assert result["status"] == "missing_product_fields"
    assert "base_price" in result["missing_fields"]

def test_rfq_without_email_does_not_create_activity(monkeypatch):
    called = []
    monkeypatch.setattr("agents.rfq.add_activity", lambda *args: called.append(args))
    result = RFQAgent().create_draft({"name": "Product"}, {"id": 7})
    assert result["status"] == "no_email"
    assert called == []
