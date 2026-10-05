from datetime import datetime, timezone, timedelta
from app.db import add_activity, update_lead

class FollowUpAgent:
    CADENCE = (3, 7, 14)
    def schedule_initial(self, lead_id):
        dt=(datetime.now(timezone.utc)+timedelta(days=self.CADENCE[0])).isoformat()
        update_lead(lead_id,next_follow_up=dt)
        return dt
    def schedule_next(self, lead, attempt=1):
        days=self.CADENCE[min(max(attempt,0),len(self.CADENCE)-1)]
        dt=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
        update_lead(lead['id'],next_follow_up=dt)
        return dt
    def create_draft(self, lead, attempt=1):
        email=lead.get('email')
        if not email: return {'status':'no_email'}
        body=(f"Hello {lead.get('company_name') or 'there'},\n\n"
              "I’m following up regarding our export supply opportunity. If this product is relevant to your purchasing program, I can send specifications, MOQ, capacity and a commercial offer.\n\nBest regards")
        aid=add_activity(lead['id'],'follow_up',f'Export supply follow-up #{attempt}',body,'draft')
        next_date=self.schedule_next(lead,attempt)
        return {'status':'draft_only','activity_id':aid,'to':email,'body':body,'next_follow_up':next_date}
