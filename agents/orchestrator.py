from agents.market_hunter import MarketHunter
from agents.buyer_hunter import BuyerHunter
from agents.verifier import VerificationAgent
from agents.matcher import MatchAgent
from agents.outreach import OutreachAgent
from agents.deal_intelligence import DealIntelligence
from app.db import upsert_lead, add_activity
from agents.followup import FollowUpAgent


class Orchestrator:
    def run(self, product, run_id):
        markets = MarketHunter().run(product)
        discovery_results = BuyerHunter().run(product, markets)
        # Diagnostic/provider-status records are not buyers and must never become CRM leads.
        candidates = [
            buyer for buyer in discovery_results
            if buyer.get("status") == "candidate" and buyer.get("url")
        ]
        discovery_diagnostics = [
            item for item in discovery_results
            if item.get("status") != "candidate" or not item.get("url")
        ]
        verified = VerificationAgent().run(candidates)
        matches = MatchAgent().run(product, verified)
        outreach = OutreachAgent().run(product, matches)
        deals = DealIntelligence().run(product, matches)
        lead_ids = []
        followups = []
        for match in matches:
            lead_id = upsert_lead(match)
            lead_ids.append(lead_id)
            if match.get("contact", {}).get("emails") and (match.get("match_score") or 0) >= 60:
                followup = FollowUpAgent().schedule_initial(lead_id)
                followups.append({"lead_id": lead_id, "next_follow_up": followup})
                add_activity(lead_id, "discovery", "Buyer discovered", match.get("url", ""), "recorded")
        return {
            "run_id": run_id,
            "status": "human_review_required",
            "markets": markets,
            "buyer_discovery_diagnostics": discovery_diagnostics,
            "buyers": verified,
            "matches": matches,
            "outreach": outreach,
            "deal_intelligence": deals,
            "lead_ids": lead_ids,
            "followups": followups,
            "approval_gates": [
                "commercial_offer", "final_price", "contract", "payment", "compliance_exceptions"
            ],
        }
