from agents.quote import QuoteAgent

def product():
    return {
        "name": "Iranian Dates", "hs_code": "080410", "unit": "kg",
        "base_price": 2.5, "currency": "USD", "moq": 1000,
        "shipping": .1, "insurance": .02, "duties": .0, "taxes": .0,
        "payment_fees": .03, "inspection": .01, "warehousing": .0,
        "financing": .0, "returns_or_waste": .04,
    }

def test_quote_is_transparent_and_human_review_only():
    result = QuoteAgent().create_draft(product(), {"company_name": "Buyer LLC", "country": "Oman"})
    assert result["status"] == "draft_only"
    assert result["decision"] == "human_review_required"
    assert result["commercials"]["factory_base_price"] == 2.5
    assert result["commercials"]["landed_cost"] == 2.7
    assert result["commercials"]["indicative_buyer_price"] > 2.7
    assert "final_price" in result["approval_required"]

def test_quote_requires_all_cost_inputs():
    p = product()
    del p["shipping"]
    result = QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"})
    assert result["status"] == "pending_cost_inputs"
    assert "shipping" in result["missing_inputs"]

def test_quote_rejects_missing_buyer():
    result = QuoteAgent().create_draft(product(), {})
    assert result["status"] == "missing_buyer_fields"


def test_quote_rejects_negative_and_non_finite_costs():
    for bad in (-1, float("nan"), float("inf"), "not-a-number"):
        p = product()
        p["shipping"] = bad
        result = QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"})
        assert result["status"] == "invalid_cost_input"
        assert result["field"] == "shipping"


def test_quote_rejects_invalid_currency_margin_and_validity():
    p = product()
    p["currency"] = "US dollars"
    assert QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"})["status"] == "invalid_currency"

    p = product()
    assert QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"}, target_margin_pct=float("nan"))["status"] == "invalid_margin"
    assert QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"}, validity_days=0)["status"] == "invalid_validity_days"


def test_quote_rejects_missing_product_name_without_raising():
    p = product()
    del p["name"]
    result = QuoteAgent().create_draft(p, {"company_name": "Buyer LLC"})
    assert result["status"] == "missing_product_fields"
    assert "name" in result["missing_fields"]
