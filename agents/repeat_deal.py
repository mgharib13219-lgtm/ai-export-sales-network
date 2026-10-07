from datetime import datetime, timezone

class RepeatDealEngine:
    """Deterministic repeat-order protection and commission policy."""

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
        source_country = self._norm(source_deal.get("country"))
        target_country = self._norm(country or lead.get("country"))
        source_product = self._norm(source_deal.get("product_name"))
        product = self._norm(product_name)
        identity_matches = ((source_buyer and buyer and source_buyer == buyer) or
            (source_country and target_country and source_country == target_country and source_product and product and source_product == product) or
            (source_buyer and buyer and (source_buyer in buyer or buyer in source_buyer)))
        active = bool(source_deal.get("repeat_eligible")) and bool(until and now <= until)
        protected = active and bool(identity_matches)
        return {
            "protected": protected, "anti_circumvention": protected,
            "contractual_basis_required": True, "protection_days_default": self.protection_days,
            "repeat_until": until.isoformat() if until else None,
            "identity_match": bool(identity_matches),
            "reason": "repeat_commission_protected" if protected else "outside_repeat_protection_or_identity_mismatch"
        }

    def commission(self, source_deal, quantity, unit_price, explicit_commission=None):
        total = float(quantity) * float(unit_price)
        source_total = float(source_deal.get("quantity") or 0) * float(source_deal.get("agreed_unit_price") or 0)
        source_commission = float(source_deal.get("network_commission") or 0)
        basis = (source_commission / source_total) if source_total > 0 else 0.0
        amount = float(explicit_commission) if explicit_commission is not None else round(total * basis, 6)
        return {"network_commission": round(amount, 6), "commission_basis": round(basis, 10),
                "commission_currency": source_deal.get("currency"), "calculated": explicit_commission is None}
