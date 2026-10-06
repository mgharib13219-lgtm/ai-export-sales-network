class QuoteAgent:
    """Build a transparent commercial quotation draft. Never sends or approves a quote."""
    REQUIRED_BUYER_FIELDS = ("company_name",)
    COST_FIELDS = (
        "shipping", "insurance", "duties", "taxes", "payment_fees",
        "inspection", "warehousing", "financing", "returns_or_waste",
    )

    def create_draft(self, product, buyer, target_margin_pct=10.0, incoterm="TBD", payment_terms="TBD", validity_days=7):
        if not buyer.get("company_name"):
            return {"status": "missing_buyer_fields", "missing_fields": ["company_name"]}
        if product.get("base_price") is None:
            return {"status": "missing_product_fields", "missing_fields": ["base_price"]}
        if not product.get("currency"):
            return {"status": "missing_product_fields", "missing_fields": ["currency"]}

        missing = [f for f in self.COST_FIELDS if product.get(f) is None]
        if missing:
            return {
                "status": "pending_cost_inputs",
                "missing_inputs": missing,
                "decision": "human_review_required",
            }

        landed_cost = float(product["base_price"]) + sum(float(product[f]) for f in self.COST_FIELDS)
        margin_pct = float(target_margin_pct)
        if margin_pct < 0 or margin_pct >= 100:
            return {"status": "invalid_margin"}

        target_price = landed_cost / (1 - margin_pct / 100)
        network_fee = max(0.0, target_price - float(product["base_price"]))
        return {
            "status": "draft_only",
            "decision": "human_review_required",
            "buyer": {
                "company_name": buyer["company_name"],
                "country": buyer.get("country"),
                "email": buyer.get("email"),
            },
            "product": {
                "name": product["name"],
                "hs_code": product.get("hs_code"),
                "unit": product.get("unit"),
                "moq": product.get("moq"),
                "currency": product["currency"],
            },
            "commercials": {
                "factory_base_price": float(product["base_price"]),
                "costs": {f: float(product[f]) for f in self.COST_FIELDS},
                "landed_cost": round(landed_cost, 6),
                "target_margin_pct": margin_pct,
                "indicative_buyer_price": round(target_price, 6),
                "network_value_above_base": round(network_fee, 6),
            },
            "terms": {
                "incoterm": incoterm,
                "payment_terms": payment_terms,
                "validity_days": int(validity_days),
            },
            "approval_required": [
                "final_price", "margin", "incoterm", "payment_terms", "commercial_offer"
            ],
        }
