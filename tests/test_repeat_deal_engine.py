from datetime import datetime, timedelta, timezone

import pytest

from agents.repeat_deal import RepeatDealEngine


def _source(**overrides):
    row = {
        "buyer_company": "Buyer Co",
        "repeat_eligible": True,
        "repeat_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "quantity": 100,
        "agreed_unit_price": 10,
        "network_commission": 20,
        "currency": "USD",
    }
    row.update(overrides)
    return row


def test_repeat_protection_requires_same_buyer_identity():
    engine = RepeatDealEngine()
    lead = {"company_name": "Different Buyer Ltd"}
    result = engine.evaluate(_source(), lead, "Dates")
    assert result["protected"] is False
    assert result["identity_match"] is False


def test_repeat_protection_expires_at_contractual_deadline():
    engine = RepeatDealEngine()
    now = datetime.now(timezone.utc)
    source = _source(repeat_until=(now - timedelta(seconds=1)).isoformat())
    result = engine.evaluate(source, {"company_name": "Buyer Co"}, "Dates", now=now)
    assert result["protected"] is False
    assert result["contractual_basis_required"] is True


def test_repeat_commission_uses_source_deal_rate():
    result = RepeatDealEngine().commission(_source(), quantity=50, unit_price=12)
    assert result["network_commission"] == 12
    assert result["commission_currency"] == "USD"
    assert result["calculated"] is True


@pytest.mark.parametrize("quantity,unit_price,commission", [
    (0, 10, None),
    (1, 0, None),
    (1, 10, -1),
    (1, 10, 11),
])
def test_repeat_commission_rejects_invalid_values(quantity, unit_price, commission):
    with pytest.raises(ValueError):
        RepeatDealEngine().commission(
            _source(), quantity, unit_price, explicit_commission=commission
        )
