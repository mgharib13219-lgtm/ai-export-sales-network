"""Conservative, idempotent follow-up drafts. No message is sent."""
from datetime import datetime, timezone, timedelta
from app.db import add_activity, update_lead, list_activities, claim_idempotency, complete_idempotency, fail_idempotency


class FollowUpAgent:
    CADENCE = (3, 7, 14)

    def schedule_initial(self, lead_id):
        dt = (datetime.now(timezone.utc) + timedelta(days=self.CADENCE[0])).isoformat()
        update_lead(lead_id, next_follow_up=dt)
        return dt

    def schedule_next(self, lead, attempt=1):
        days = self.CADENCE[min(max(int(attempt), 0), len(self.CADENCE) - 1)]
        dt = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        update_lead(lead["id"], next_follow_up=dt)
        return dt

    def create_draft(self, lead, attempt=None):
        if not lead or not lead.get("id"):
            return {"status": "lead_not_found"}
        if lead.get("stage") in ("won", "lost", "repeat"):
            return {"status": "terminal_lead"}
        if attempt is not None and (not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 20):
            return {"status": "invalid_attempt"}
        if attempt is None:
            prior = [x for x in list_activities(lead['id'], limit=500) if x.get('kind') == 'follow_up']
            attempt = len(prior) + 1
        if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 20:
            return {"status": "invalid_attempt"}
        email = lead.get("email")
        if not email:
            return {"status": "no_email"}
        idem_key = f"followup-draft:{lead['id']}:{attempt}"
        claim = claim_idempotency(idem_key)
        if not claim.get("claimed"):
            cached = claim.get("payload") or {}
            if claim.get("status") == "completed":
                return {**cached, "status": "already_created"}
            return {"status": "already_processing", "retry_after_seconds": 30}
        body = (
            f"Hello {lead.get('company_name') or 'there'},\n\n"
            "I’m following up regarding our export supply opportunity. If this product is relevant "
            "to your purchasing program, I can send specifications, MOQ, capacity and a commercial offer.\n\n"
            "Best regards"
        )
        try:
            aid = add_activity(lead["id"], "follow_up", f"Export supply follow-up #{attempt}", body, "draft")
            next_date = self.schedule_next(lead, attempt)
            result = {"status": "draft_only", "activity_id": aid, "to": email,
                      "body": body, "next_follow_up": next_date, "approval_required": True,
                      "sent": False}
            complete_idempotency(idem_key, result)
            return result
        except Exception as exc:
            fail_idempotency(idem_key, {"error": "draft_creation_failed"})
            raise exc
