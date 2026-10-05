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
        buyers = BuyerHunter().run(product, markets)
        verified = VerificationAgent().run(buyers)
        matches = MatchAgent().run(product, verified)
        outreach = OutreachAgent().run(product, matches)
        deals = DealIntelligence().run(product, matches)
        lead_ids=[]
        followups=[]
        for m in matches:
            lid=upsert_lead(m)
            lead_ids.append(lid)
            if m.get('contact',{}).get('emails') and (m.get('match_score') or 0) >= 60:
                f=FollowUpAgent().schedule_initial(lid)
                followups.append({'lead_id':lid,'next_follow_up':f})
                add_activity(lid,'discovery','Buyer discovered',m.get('url',''),'recorded')
        return {
            "run_id": run_id,
            "status": "human_review_required",
            "markets": markets,
            "buyers": verified,
            "matches": matches,
            "outreach": outreach,
            "deal_intelligence": deals,
            "lead_ids": lead_ids,
            "followups": followups,
            "approval_gates": ["commercial_offer", "final_price", "contract", "payment", "compliance_exceptions"]
        }
