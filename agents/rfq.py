from app.db import add_activity

class RFQAgent:
    REQUIRED_FIELDS = ("name", "description", "hs_code", "unit", "base_price", "currency", "moq")

    def create_draft(self, product, lead):
        if not lead.get("email"):
            return {"status": "no_email", "decision": "manual_contact_required"}

        missing = [field for field in self.REQUIRED_FIELDS if not product.get(field)]
        company = lead.get("company_name") or "Purchasing Team"
        if missing:
            return {
                "status": "missing_product_fields",
                "missing_fields": missing,
                "decision": "human_review_required",
            }

        subject = f"RFQ / Commercial Inquiry — {product['name']}"
        body = (
            f"Dear {company},\n\n"
            f"We would like to provide a quotation for {product['name']}.\n"
            f"Product description: {product['description']}\n"
            f"HS Code: {product['hs_code']}\n"
            f"Unit: {product['unit']}\n"
            f"Indicative base price: {product['base_price']} {product['currency']}\n"
            f"MOQ: {product['moq']}\n\n"
            "Please confirm your required quantity, destination, preferred Incoterm, "
            "payment terms and required certificates so the final commercial offer "
            "can be prepared.\n\n"
            "This is a draft for human review and approval before sending.\n\n"
            "Best regards"
        )
        activity_id = add_activity(
            lead["id"], "rfq", subject, body, "draft"
        )
        return {
            "status": "draft_only",
            "decision": "human_review_required",
            "activity_id": activity_id,
            "to": lead["email"],
            "subject": subject,
            "body": body,
        }
