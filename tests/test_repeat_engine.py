from datetime import datetime, timedelta, timezone

from agents.repeat_deal import RepeatDealEngine


def test_repeat_protection_requires_same_buyer_identity():
    engine = RepeatDealEngine()
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    source = {
        "buyer_company": "Buyer Alpha Ltd",
        "product_name": "Iranian Dates",
        "country": "Oman",
        "repeat_eligible": True,
        "repeat_until": (now + timedelta(days=30)).isoformat(),
    }
    same_buyer = engine.evaluate(source, {"company_name": "  buyer alpha ltd "}, "Iranian Dates", now=now)
    other_buyer_same_market = engine.evaluate(
        source, {"company_name": "Buyer Beta Ltd", "country": "Oman"},
        "Iranian Dates", buyer_company="Buyer Beta Ltd", country="Oman", now=now,
    )
    assert same_buyer["protected"] is True
    assert other_buyer_same_market["protected"] is False
    assert other_buyer_same_market["identity_match"] is False


def test_repeat_protection_expires():
    engine = RepeatDealEngine()
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    source = {
        "buyer_company": "Buyer Alpha Ltd",
        "repeat_eligible": True,
        "repeat_until": (now - timedelta(seconds=1)).isoformat(),
    }
    result = engine.evaluate(source, {"company_name": "Buyer Alpha Ltd"}, "Iranian Dates", now=now)
    assert result["protected"] is False


def test_repeat_commission_rejects_amount_above_order_total():
    engine = RepeatDealEngine()
    source = {"quantity": 100, "agreed_unit_price": 2, "network_commission": 10, "currency": "USD"}
    try:
        engine.commission(source, 10, 2, explicit_commission=21)
    except ValueError as exc:
        assert str(exc) == "network_commission_outside_deal_value"
    else:
        raise AssertionError("commission above order value must be rejected")
