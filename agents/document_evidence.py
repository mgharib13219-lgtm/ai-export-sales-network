"""Review supplier-provided document metadata without claiming authenticity or verification."""
from datetime import date, timedelta


class DocumentEvidenceAgent:
    REQUIRED_DOCUMENTS = (
        "business_registration", "representative_authority", "product_specification",
        "certificate_evidence", "facility_or_production_evidence",
    )

    def run(self, evidence, required_documents=None, today=None, expiry_warning_days=30):
        evidence = evidence if isinstance(evidence, dict) else {}
        required = tuple(required_documents or self.REQUIRED_DOCUMENTS)
        today = date.fromisoformat(today) if isinstance(today, str) else (today or date.today())
        missing, expired, expiring, supplied = [], [], [], []
        for key in required:
            item = evidence.get(key)
            if not item:
                missing.append(key)
                continue
            supplied.append(key)
            expiry = item.get("expires_at") if isinstance(item, dict) else None
            if expiry:
                try:
                    expiry_date = date.fromisoformat(str(expiry)[:10])
                except (TypeError, ValueError):
                    expired.append({"document": key, "reason": "invalid_expiry_date"})
                    continue
                if expiry_date < today:
                    expired.append({"document": key, "expires_at": expiry_date.isoformat()})
                elif expiry_date <= today + timedelta(days=expiry_warning_days):
                    expiring.append({"document": key, "expires_at": expiry_date.isoformat()})
        issues = (["missing_documents"] if missing else [])
        if expired:
            issues.append("expired_or_invalid_expiry")
        if expiring:
            issues.append("documents_expiring_soon")
        return {
            "agent": "document_evidence", "status": "NEEDS_REVIEW" if issues else "READY_FOR_HUMAN_REVIEW",
            "required_documents": list(required), "supplied_documents": supplied,
            "missing_documents": missing, "expired_documents": expired, "expiring_soon": expiring,
            "authenticity_verified": False, "issuer_verified": False, "contents_extracted": False,
            "legal_or_compliance_clearance": False, "human_review_required": True, "issues": issues,
        }
