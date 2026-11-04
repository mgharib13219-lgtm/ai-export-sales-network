"""Counteroffer review and aggregate learning from recorded deal outcomes."""
import math
from collections import defaultdict


class NegotiationAgent:
    """Evaluate buyer counteroffers without accepting them."""
    def evaluate_counteroffer(self, quote, counter_unit_price, max_discount_pct=5.0):
        try:
            counter = float(counter_unit_price)
            target = float((quote or {}).get("commercials", {}).get("indicative_buyer_price", 0))
            discount = float(max_discount_pct)
        except (TypeError, ValueError, OverflowError):
            return {"status": "invalid_counteroffer"}
        if not all(math.isfinite(x) for x in (counter, target, discount)) or counter <= 0:
            return {"status": "invalid_counteroffer"}
        if target <= 0:
            return {"status": "missing_quote_target"}
        if discount < 0 or discount >= 100:
            return {"status": "invalid_discount_limit"}
        variance_pct = (counter - target) / target * 100
        acceptable_floor = target * (1 - discount / 100)
        within_bounds = counter >= acceptable_floor
        return {
            "status": "review_required", "decision": "human_review_required",
            "target_price": round(target, 6), "counter_unit_price": round(counter, 6),
            "variance_pct": round(variance_pct, 4), "acceptable_floor": round(acceptable_floor, 6),
            "within_approval_bounds": within_bounds,
            "recommendation": "counter_or_accept_after_human_review" if within_bounds else "escalate_for_human_review",
            "never_auto_accept": True,
        }


class NegotiationLearningAgent:
    """Deterministic aggregate statistics; never trains or changes pricing policy."""
    MIN_SAMPLE = 3

    def summarize(self, outcomes):
        groups = defaultdict(list)
        valid = 0
        for item in outcomes or []:
            if not isinstance(item, dict) or item.get("outcome") not in ("won", "lost"):
                continue
            price = item.get("accepted_unit_price")
            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError, OverflowError):
                price = None
            if price is not None and (not math.isfinite(price) or price <= 0):
                price = None
            key = (str(item.get("currency") or "UNKNOWN").upper(),
                   str(item.get("incoterm") or "UNSPECIFIED").upper(),
                   str(item.get("payment_terms") or "UNSPECIFIED").lower())
            groups[key].append({"outcome": item["outcome"], "price": price})
            valid += 1
        segments = []
        for (currency, incoterm, payment_terms), rows in sorted(groups.items()):
            if len(rows) < self.MIN_SAMPLE:
                continue
            wins = [r for r in rows if r["outcome"] == "won"]
            prices = [r["price"] for r in wins if r["price"] is not None]
            segments.append({
                "currency": currency, "incoterm": incoterm, "payment_terms": payment_terms,
                "sample_size": len(rows), "wins": len(wins), "losses": len(rows) - len(wins),
                "win_rate_pct": round(len(wins) / len(rows) * 100, 2),
                "average_won_unit_price": round(sum(prices) / len(prices), 6) if prices else None,
                "price_sample_size": len(prices), "pricing_policy_changed": False,
            })
        return {
            "status": "insufficient_history" if not segments else "aggregate_insights_ready",
            "outcome_count": valid, "minimum_segment_sample": self.MIN_SAMPLE,
            "segments": segments, "automatic_price_adjustment": False,
            "human_review_required": True,
        }
