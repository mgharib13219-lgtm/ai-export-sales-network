from datetime import datetime, timezone

class RepeatDealEngine:
    """Deterministic repeat-order protection and commission policy.

    Protection is tied to the same buyer identity, not merely the same product
    or destination country. Legal enforceability still depends on the signed
    agreement and applicable law.
    """

    def __init__(self, protection_days=1095):
        self.protection_days = max(1, int(protection_days))

    @staticmethod
    def _norm(value):
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None

    def evaluate(self, source_deal, lead, product_name, buyer_company=None, country=None, now=None):
        now = now or datetime.now(timezone.utc)
        until = self._date(source_deal.get("repeat_until"))
        source_buyer = self._norm(source_deal.get("buyer_company"))
        buyer = self._norm(buyer_company or lead.get("company_name"))
        # Do not protect unrelated buyers just because they buy the same product
        # or operate in the same country. Alias matching requires verified data.
        identity_matches = bool(source_buyer and buyer and source_buyer == buyer)
        active = bool(source_deal.get("repeat_eligible")) and bool(until and now <= until)
        protected = active and identity_matches
        return {
            "protected": protected,
            "anti_circumvention": protected,
            "contractual_basis_required": True,
            "protection_days_default": self.protection_days,
            "repeat_until": until.isoformat() if until else None,
            "identity_match": identity_matches,
            "reason": "repeat_commission_protected" if protected else "outside_repeat_protection_or_identity_mismatch",
        }

    def commission(self, source_deal, quantity, unit_price, explicit_commission=None):
        quantity = float(quantity)
        unit_price = float(unit_price)
        if quantity <= 0 or unit_price <= 0:
            raise ValueError("quantity_and_unit_price_must_be_positive")
        total = quantity * unit_price
        source_total = float(source_deal.get("quantity") or 0) * float(source_deal.get("agreed_unit_price") or 0)
        source_commission = float(source_deal.get("network_commission") or 0)
        if source_commission < 0 or source_total < 0:
            raise ValueError("source_commission_and_total_must_not_be_negative")
        basis = (source_commission / source_total) if source_total > 0 else 0.0
        amount = float(explicit_commission) if explicit_commission is not None else round(total * basis, 6)
        if amount < 0 or amount > total:
            raise ValueError("network_commission_outside_deal_value")
        return {
            "network_commission": round(amount, 6),
            "commission_basis": round(basis, 10),
            "commission_currency": source_deal.get("currency"),
            "calculated": explicit_commission is None,
        }
