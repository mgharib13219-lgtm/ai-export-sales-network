from agents.deal_builder import DealBuilderAgent


def sample_product():
    return {
        "name": "Olive oil", "base_price": 10, "currency": "EUR",
        "shipping": 1, "insurance": 0.1, "duties": 0, "taxes": 0,
        "payment_fees": 0.1, "inspection": 0.1, "warehousing": 0,
        "financing": 0, "returns_or_waste": 0.2,
    }


def test_deal_builder_fails_closed_without_compliance_review():
    result = DealBuilderAgent().build(sample_product(), {"company_name": "Buyer GmbH"})
    assert result["status"] == "blocked_pending_compliance_review"
    assert result["external_actions_performed"] is False


def test_deal_builder_requires_buyer_identity_review():
    result = DealBuilderAgent().build(
        sample_product(), {"company_name": "Buyer GmbH"}, compliance_reviewed=True
    )
    assert result["status"] == "blocked_pending_buyer_identity_review"


def test_deal_builder_creates_only_reviewable_draft():
    result = DealBuilderAgent().build(
        sample_product(), {"company_name": "Buyer GmbH"},
        compliance_reviewed=True, buyer_identity_reviewed=True,
        incoterm="FCA", payment_terms="30% advance, balance against documents",
    )
    assert result["status"] == "draft_only"
    assert result["quote"]["status"] == "draft_only"
    assert result["approval_required"] is True
    assert result["quote_sent"] is False
    assert result["contract_created"] is False


def test_deal_builder_returns_missing_costs_instead_of_guessing():
    product = sample_product()
    del product["shipping"]
    result = DealBuilderAgent().build(
        product, {"company_name": "Buyer GmbH"},
        compliance_reviewed=True, buyer_identity_reviewed=True,
    )
    assert result["status"] == "incomplete_commercial_inputs"
    assert "shipping" in result["quote"]["missing_inputs"]
