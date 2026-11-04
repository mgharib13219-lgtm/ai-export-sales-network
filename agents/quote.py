"""Build a transparent commercial quotation draft. Never sends or approves a quote."""
import math
import re


class QuoteAgent:
    REQUIRED_BUYER_FIELDS = ("company_name",)
    COST_FIELDS = (
        "shipping", "insurance", "duties", "taxes", "payment_fees",
        "inspection", "warehousing", "financing", "returns_or_waste",
    )

    @staticmethod
    def _finite_number(value):
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    def create_draft(self, product, buyer, target_margin_pct=10.0, incoterm="TBD",
                     payment_terms="TBD", validity_days=7):
        product = product if isinstance(product, dict) else {}
        buyer = buyer if isinstance(buyer, dict) else {}
        if not str(buyer.get("company_name") or "").strip():
            return {"status": "missing_buyer_fields", "missing_fields": ["company_name"]}

        missing = []
        if not str(product.get("name") or "").strip():
            missing.append("name")
        if product.get("base_price") is None:
            missing.append("base_price")
        if not product.get("currency"):
            missing.append("currency")
        if missing:
            return {"status": "missing_product_fields", "missing_fields": missing}

        currency = str(product["currency"]).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            return {"status": "invalid_currency", "field": "currency"}

        base_price = self._finite_number(product["base_price"])
        if base_price is None or base_price < 0:
            return {"status": "invalid_cost_input", "field": "base_price"}

        missing_costs = [field for field in self.COST_FIELDS if product.get(field) is None]
        if missing_costs:
            return {
                "status": "pending_cost_inputs",
                "missing_inputs": missing_costs,
                "decision": "human_review_required",
            }

        costs = {}
        for field in self.COST_FIELDS:
            value = self._finite_number(product[field])
            if value is None or value < 0:
                return {"status": "invalid_cost_input", "field": field}
            costs[field] = value

        margin_pct = self._finite_number(target_margin_pct)
        if margin_pct is None or margin_pct < 0 or margin_pct >= 100:
            return {"status": "invalid_margin"}
        if isinstance(validity_days, bool) or not isinstance(validity_days, int) or not 1 <= validity_days <= 365:
            return {"status": "invalid_validity_days"}

        landed_cost = base_price + sum(costs.values())
        target_price = landed_cost / (1 - margin_pct / 100)
        return {
            "status": "draft_only",
            "decision": "human_review_required",
            "buyer": {
                "company_name": str(buyer["company_name"]).strip(),
                "country": buyer.get("country"),
                "email": buyer.get("email"),
            },
            "product": {
                "name": str(product["name"]).strip(),
                "hs_code": product.get("hs_code"),
                "unit": product.get("unit"),
                "moq": product.get("moq"),
                "currency": currency,
            },
            "commercials": {
                "factory_base_price": base_price,
                "costs": costs,
                "landed_cost": round(landed_cost, 6),
                "target_margin_pct": margin_pct,
                "indicative_buyer_price": round(target_price, 6),
                "network_value_above_base": round(max(0.0, target_price - base_price), 6),
            },
            "terms": {
                "incoterm": str(incoterm or "TBD").strip() or "TBD",
                "payment_terms": str(payment_terms or "TBD").strip() or "TBD",
                "validity_days": validity_days,
            },
            "approval_required": [
                "final_price", "margin", "incoterm", "payment_terms", "commercial_offer"
            ],
        }
