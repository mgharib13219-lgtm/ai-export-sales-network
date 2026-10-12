from app.providers import ai_provider, contact_extractor


class VerificationAgent:
    """Collect public evidence; never treat automated analysis as legal/company verification."""

    def _score(self, buyer, analysis):
        parsed = (analysis or {}).get("parsed") or {}
        evidence = 0
        evidence += 15 if buyer.get("contact", {}).get("emails") else 0
        evidence += 10 if buyer.get("contact", {}).get("phones") else 0
        evidence += 15 if buyer.get("contact", {}).get("contact_pages") else 0
        evidence += 10 if buyer.get("website", {}).get("reachable") else 0
        evidence += 10 if buyer.get("buyer_signals") else 0
        ai_score = parsed.get("score") if isinstance(parsed.get("score"), (int, float)) else 0
        return max(0, min(100, round(evidence + ai_score * 0.4)))

    def run(self, buyers):
        out = []
        for buyer in buyers:
            if not buyer.get("url"):
                out.append({
                    **buyer,
                    "verification": {
                        "status": "pending",
                        "score": 0,
                        "risk_flags": ["no_url"],
                        "evidence_sources": [],
                        "decision": "human_review_required",
                        "identity_verified": False,
                    },
                })
                continue

            contact = contact_extractor.extract(buyer["url"])
            enriched = {
                **buyer,
                "website": contact.get("website", {}),
                "contact": contact.get("contact", {}),
                "buyer_signals": contact.get("buyer_signals", []),
            }
            website = enriched["website"]
            contacts = enriched["contact"]
            analysis = ai_provider.analyze("buyer_verification", enriched)
            score = self._score(enriched, analysis)
            parsed = (analysis or {}).get("parsed") or {}
            risk_flags = list(parsed.get("risk_flags") or [])

            if not website.get("reachable"):
                status = "site_unreachable"
                risk_flags.append("website_unreachable")
            elif (analysis or {}).get("status") == "not_configured":
                status = "ai_review_unavailable"
                risk_flags.append("ai_provider_not_configured")
            elif (analysis or {}).get("status") != "ok" or not parsed:
                status = "ai_review_error"
                risk_flags.append("ai_analysis_failed")
            elif score < 40:
                status = "insufficient_evidence"
                risk_flags.append("low_evidence_score")
            else:
                status = "review_required"
                risk_flags.append("automated_review_not_identity_proof")

            evidence_sources = []
            if website.get("reachable") and website.get("final_url"):
                evidence_sources.append({
                    "type": "public_website",
                    "url": website["final_url"],
                    "status_code": website.get("status_code"),
                })
            evidence_sources.extend(
                {"type": "public_contact_page", "url": page}
                for page in contacts.get("contact_pages", [])
            )
            out.append({
                **enriched,
                "verification": {
                    "status": status,
                    "score": score,
                    "company_name": parsed.get("company_name") or buyer.get("title"),
                    "buyer_type": parsed.get("buyer_type"),
                    "risk_flags": sorted(set(risk_flags)),
                    "evidence": parsed.get("evidence", []),
                    "evidence_sources": evidence_sources,
                    "contact_evidence": {
                        "email_count": len(contacts.get("emails", [])),
                        "phone_count": len(contacts.get("phones", [])),
                        "contact_page_count": len(contacts.get("contact_pages", [])),
                    },
                    "analysis": analysis,
                    "decision": "human_review_required",
                    "identity_verified": False,
                },
            })
        return out
