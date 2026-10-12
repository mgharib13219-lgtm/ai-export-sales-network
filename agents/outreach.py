from app.providers import ai_provider


class OutreachAgent:
    def run(self, product, matches):
        out = []
        for match in matches:
            emails = match.get("contact", {}).get("emails", [])
            if not emails:
                continue
            verification = match.get("verification", {})
            analysis = ai_provider.analyze("outreach_writer", {"product": product, "buyer": match})
            parsed = analysis.get("parsed") or {}
            out.append({
                "market": match.get("market"),
                "buyer": match.get("title") or verification.get("company_name"),
                "email": emails[0],
                "channel": "email",
                "status": "draft_only",
                "draft": parsed or analysis,
                "verification_status": verification.get("status", "not_checked"),
                "verification_score": verification.get("score", 0),
                "risk_flags": verification.get("risk_flags", []),
                "recommended_next_action": verification.get("recommended_next_action", "human_review_public_evidence"),
                "identity_verified": False,
                "approval_required": True,
            })
        return out
