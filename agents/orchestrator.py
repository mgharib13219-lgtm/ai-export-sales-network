from agents.market_hunter import MarketHunter
from agents.buyer_hunter import BuyerHunter
from agents.verifier import VerificationAgent
from agents.matcher import MatchAgent
from agents.outreach import OutreachAgent
from agents.deal_intelligence import DealIntelligence
from agents.followup import FollowUpAgent
from agents.compliance_gatekeeper import ComplianceGatekeeper
from agents.supplier_onboarding import SupplierOnboardingAgent
from agents.catalogue_editor import CatalogueEditorAgent
from agents.quality_auditor import QualityAuditorAgent
from app.db import upsert_lead, add_activity


class Orchestrator:
    def run(self, product, run_id):
        # Run the compliance preflight before buyer discovery or matching.
        compliance = ComplianceGatekeeper().run(product)
        supplier_profile = SupplierOnboardingAgent().run({
            "company_name": product.get("supplier_company_name"),
            "country": product.get("supplier_country"),
            "evidence": product.get("supplier_evidence") or {},
        }, product)
        catalogue = CatalogueEditorAgent().run(product)

        if compliance["status"] == "BLOCKED":
            result = {
                "run_id": run_id,
                "status": "blocked_pending_compliance_review",
                "compliance_review": compliance,
                "supplier_onboarding": supplier_profile,
                "catalogue_draft": catalogue,
                "markets": [],
                "buyer_discovery_diagnostics": [],
                "buyers": [],
                "matches": [],
                "outreach": [],
                "deal_intelligence": {"status": "blocked_pending_compliance_review"},
                "lead_ids": [],
                "followups": [],
                "approval_gates": ["compliance_review", "party_screening", "end_use_review"],
            }
            result["quality_audit"] = QualityAuditorAgent().run(result)
            return result

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
        # A preflight checklist is not legal clearance; keep this hold attached to every match.
        for match in matches:
            match["compliance_status"] = compliance["status"]
            match["compliance_clearance"] = False
            match["human_compliance_review_required"] = True

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

        result = {
            "run_id": run_id,
            "status": "human_review_required",
            "compliance_review": compliance,
            "supplier_onboarding": supplier_profile,
            "catalogue_draft": catalogue,
            "markets": markets,
            "buyer_discovery_diagnostics": discovery_diagnostics,
            "buyers": verified,
            "matches": matches,
            "outreach": outreach,
            "deal_intelligence": deals,
            "lead_ids": lead_ids,
            "followups": followups,
            "approval_gates": [
                "business_identity", "party_screening", "end_user_and_end_use",
                "commercial_offer", "final_price", "contract", "payment", "compliance_exceptions"
            ],
        }
        result["quality_audit"] = QualityAuditorAgent().run(result)
        return result
