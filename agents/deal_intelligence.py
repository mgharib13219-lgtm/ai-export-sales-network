class DealIntelligence:
    def run(self, product, matches):
        base = product.get("base_price")
        return {
            "status": "pending_cost_inputs",
            "base_price": base,
            "required_inputs": [
                "shipping", "insurance", "duties", "taxes", "payment_fees",
                "inspection", "warehousing", "financing", "returns_or_waste"
            ],
            "decision": "review_required"
        }
