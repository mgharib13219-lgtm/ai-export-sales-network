"""Prepare a controlled commercial deal pack; never approve or send it."""
from agents.quote import QuoteAgent


class DealBuilderAgent:
    def build(self, product, buyer, compliance_reviewed=False, buyer_identity_reviewed=False,
              target_margin_pct=10.0, incoterm="TBD", payment_terms="TBD", validity_days=7):
        if not compliance_reviewed:
            return {
                "agent": "deal_builder",
                "status": "blocked_pending_compliance_review",
                "missing_approvals": ["compliance_reviewed"],
                "approval_required": True,
                "external_actions_performed": False,
            }
        if not buyer_identity_reviewed:
            return {
                "agent": "deal_builder",
                "status": "blocked_pending_buyer_identity_review",
                "missing_approvals": ["buyer_identity_reviewed"],
                "approval_required": True,
                "external_actions_performed": False,
            }
        quote = QuoteAgent().create_draft(
            product, buyer, target_margin_pct=target_margin_pct,
            incoterm=incoterm, payment_terms=payment_terms, validity_days=validity_days,
        )
        if quote.get("status") != "draft_only":
            return {
                "agent": "deal_builder",
                "status": "incomplete_commercial_inputs",
                "quote": quote,
                "approval_required": True,
                "external_actions_performed": False,
            }
        return {
            "agent": "deal_builder",
            "status": "draft_only",
            "quote": quote,
            "checklist": [
                "confirm_quantity_and_delivery_schedule",
                "confirm_incoterm_and_named_place",
                "confirm_payment_security_and_terms",
                "confirm_certificate_and_document_requirements",
                "review_price_margin_and_all_cost_inputs",
                "approve_final_offer_before_sending",
            ],
            "approval_required": True,
            "external_actions_performed": False,
            "contract_created": False,
            "quote_sent": False,
        }
