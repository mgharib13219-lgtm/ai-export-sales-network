"""Preflight export-risk triage. This agent never grants legal or sanctions clearance."""
from datetime import datetime, timezone


class ComplianceGatekeeper:
    REQUIRED_FIELDS = ("name", "origin", "hs_code", "target_countries")

    def run(self, product):
        product = product or {}
        missing = [field for field in self.REQUIRED_FIELDS if not product.get(field)]
        explicit_flags = []
        for key, label in (
            ("sanctions_hit", "possible_restricted_party_or_sanctions_match"),
            ("restricted_party_match", "possible_restricted_party_match"),
            ("dual_use", "possible_dual_use_or_controlled_goods"),
            ("end_use_unknown", "end_use_or_end_user_unknown"),
            ("export_license_required", "export_license_requirement_needs_review"),
        ):
            if product.get(key):
                explicit_flags.append(label)
        supplied_flags = product.get("compliance_flags") or []
        if isinstance(supplied_flags, list):
            explicit_flags.extend(str(flag)[:160] for flag in supplied_flags if flag)
        checks = [
            {"area": "product_classification", "status": "missing_input" if not product.get("hs_code") else "human_review_required"},
            {"area": "origin", "status": "missing_input" if not product.get("origin") else "human_review_required"},
            {"area": "destination", "status": "missing_input" if not product.get("target_countries") else "human_review_required"},
            {"area": "parties_and_beneficial_owners", "status": "not_screened"},
            {"area": "end_user_and_end_use", "status": "not_screened"},
            {"area": "licenses_and_product_rules", "status": "not_screened"},
        ]
        status = "BLOCKED" if explicit_flags else "NEEDS_REVIEW"
        if missing:
            status = "BLOCKED" if explicit_flags else "INSUFFICIENT_EVIDENCE"
        return {
            "agent": "compliance_gatekeeper",
            "status": status,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "missing_inputs": missing,
            "risk_flags": sorted(set(explicit_flags)),
            "checks": checks,
            "live_screening_performed": False,
            "legal_clearance": False,
            "human_approval_required": True,
            "recommended_next_step": (
                "stop_and_refer_to_qualified_compliance_reviewer" if explicit_flags
                else "complete_missing_product_and_party_data_then_run_official_screening"
            ),
            "disclaimer": "This is a preliminary checklist, not sanctions screening, export-control classification, or legal advice.",
        }
