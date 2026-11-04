"""Create conservative catalogue drafts from seller-provided facts only."""
from datetime import datetime, timezone


class CatalogueEditorAgent:
    def run(self, product, languages=None):
        product = product or {}
        name = str(product.get("name") or "").strip()
        description = str(product.get("description") or "").strip()
        if len(name) < 2:
            return {"agent": "catalogue_editor", "status": "INSUFFICIENT_EVIDENCE",
                    "missing_fields": ["name"], "human_approval_required": True}
        facts = {
            "name": name,
            "description": description or "Description not supplied by seller.",
            "hs_code": product.get("hs_code") or "NOT_PROVIDED",
            "origin": product.get("origin") or "NOT_PROVIDED",
            "unit": product.get("unit") or "NOT_PROVIDED",
            "moq": product.get("moq"),
            "capacity_per_month": product.get("capacity_per_month"),
            "certificates_claimed": list(product.get("certificates") or []),
            "currency": product.get("currency") or "NOT_PROVIDED",
        }
        lines = [name, facts["description"], f"Origin: {facts['origin']}",
                 f"HS code supplied by seller: {facts['hs_code']}",
                 f"Unit: {facts['unit']}"]
        if facts["moq"] is not None:
            lines.append(f"Minimum order quantity (seller supplied): {facts['moq']}")
        if facts["capacity_per_month"] is not None:
            lines.append(f"Monthly capacity (seller supplied): {facts['capacity_per_month']}")
        if facts["certificates_claimed"]:
            lines.append("Certificates claimed by seller (not independently verified): " +
                         ", ".join(facts["certificates_claimed"]))
        return {
            "agent": "catalogue_editor",
            "status": "draft_only",
            "source_of_facts": "seller_supplied",
            "languages_requested": list(languages or ["en"]),
            "normalized_facts": facts,
            "catalogue_draft": "\n".join(lines),
            "unsupported_claims_added": False,
            "hs_code_changed": False,
            "certificates_verified": False,
            "publication_requires_owner_approval": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
