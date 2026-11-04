"""Deterministic guardrail audit for agent pipeline outputs."""
class QualityAuditorAgent:
    def run(self, result):
        result = result or {}
        issues = []
        matches = result.get("matches") or []
        lead_ids = result.get("lead_ids") or []
        if len(lead_ids) != len(matches):
            issues.append({"code": "lead_match_count_mismatch", "severity": "high"})
        for index, match in enumerate(matches):
            verification = match.get("verification") or {}
            if verification.get("identity_verified") is True:
                issues.append({"code": "automated_identity_claim", "severity": "critical", "item": index})
            if verification.get("decision") != "human_review_required":
                issues.append({"code": "missing_identity_human_gate", "severity": "high", "item": index})
            if match.get("compliance_status") == "BLOCKED":
                issues.append({"code": "blocked_match_in_active_results", "severity": "critical", "item": index})
        for index, draft in enumerate(result.get("outreach") or []):
            if draft.get("status") != "draft_only" or draft.get("approval_required") is not True:
                issues.append({"code": "outreach_without_human_gate", "severity": "critical", "item": index})
        for index, pack in enumerate(result.get("deal_packs") or []):
            if pack.get("quote_sent") is True or pack.get("contract_created") is True:
                issues.append({"code": "deal_builder_performed_external_commitment", "severity": "critical", "item": index})
            if pack.get("approval_required") is not True:
                issues.append({"code": "deal_pack_missing_human_approval_gate", "severity": "critical", "item": index})
        for index, evidence in enumerate(result.get("document_evidence") or []):
            if evidence.get("authenticity_verified") is True or evidence.get("issuer_verified") is True:
                issues.append({"code": "automated_document_verification_claim", "severity": "critical", "item": index})
        compliance = result.get("compliance_review") or {}
        if compliance.get("status") == "BLOCKED" and matches:
            issues.append({"code": "pipeline_continued_after_compliance_block", "severity": "critical"})
        critical = any(item["severity"] == "critical" for item in issues)
        return {
            "agent": "quality_auditor",
            "status": "REJECT" if critical else ("NEEDS_REVIEW" if issues or compliance.get("status") != "COMPLETE" else "PASS"),
            "issues": issues,
            "match_count": len(matches),
            "lead_count": len(lead_ids),
            "human_review_required": True,
            "external_actions_performed": False,
        }
