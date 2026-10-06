class DealIntelligence:
    COST_FIELDS = (
        "shipping", "insurance", "duties", "taxes", "payment_fees",
        "inspection", "warehousing", "financing", "returns_or_waste",
    )

    def run(self, product, matches):
        base = product.get("base_price")
        if base is None:
            return {
                "status": "pending_base_price",
                "required_inputs": ["base_price", *self.COST_FIELDS],
                "decision": "review_required",
            }

        missing = [field for field in self.COST_FIELDS if product.get(field) is None]
        if missing:
            return {
                "status": "pending_cost_inputs",
                "base_price": base,
                "currency": product.get("currency", "USD"),
                "missing_inputs": missing,
                "provided_inputs": {
                    field: product.get(field) for field in self.COST_FIELDS
                    if product.get(field) is not None
                },
                "decision": "review_required",
            }

        costs = {field: float(product[field]) for field in self.COST_FIELDS}
        total_cost = float(base) + sum(costs.values())
        return {
            "status": "calculated",
            "base_price": float(base),
            "currency": product.get("currency", "USD"),
            "costs": costs,
            "landed_cost": total_cost,
            "margin": {
                "note": "Buyer target price and commercial terms are still required before a margin decision.",
                "decision": "review_required",
            },
            "matched_buyers": len(matches or []),
        }
