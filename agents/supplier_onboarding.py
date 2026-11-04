"""Producer onboarding assistant: structures supplied facts and identifies gaps."""
from datetime import datetime, timezone


class SupplierOnboardingAgent:
    REQUIRED_FIELDS = ("company_name", "country", "product_name", "origin", "capacity_per_month", "moq")
    EVIDENCE_FIELDS = ("business_registration", "representative_authority", "product_specification",
                       "certificate_evidence", "facility_or_production_evidence")

    def run(self, supplier, product):
        supplier = supplier or {}
        product = product or {}
        facts = {
            "company_name": supplier.get("company_name") or supplier.get("name"),
            "country": supplier.get("country"),
            "product_name": product.get("name"),
            "origin": product.get("origin"),
            "capacity_per_month": product.get("capacity_per_month"),
            "moq": product.get("moq"),
        }
        missing = [key for key, value in facts.items() if value in (None, "", [])]
        evidence = supplier.get("evidence") or {}
        evidence_gaps = [key for key in self.EVIDENCE_FIELDS if not evidence.get(key)]
        return {
            "agent": "supplier_onboarding",
            "status": "NEEDS_REVIEW" if missing or evidence_gaps else "COMPLETE",
            "profile_facts": facts,
            "missing_fields": missing,
            "evidence_gaps": evidence_gaps,
            "certificates_claimed": list(product.get("certificates") or []),
            "certificates_verified": False,
            "identity_verified": False,
            "owner_approval_required_before_publication": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "next_step": "request_missing_business_fields_and_original_evidence" if missing or evidence_gaps else "human_review_supplier_evidence",
        }
