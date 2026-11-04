from agents.followup import FollowUpAgent


def test_followup_draft_is_idempotent(monkeypatch):
    import agents.followup as module
    state = {}
    monkeypatch.setattr(module, "claim_idempotency", lambda key: (
        {"claimed": True} if key not in state else {"claimed": False, "status": "completed", "payload": state[key]}
    ))
    def complete(key, payload):
        state[key] = payload
    monkeypatch.setattr(module, "complete_idempotency", complete)
    calls = []
    monkeypatch.setattr(module, "add_activity", lambda *args: calls.append(args) or 9)
    monkeypatch.setattr(module, "update_lead", lambda *args, **kwargs: True)
    lead = {"id": 5, "email": "buyer@example.com", "company_name": "Buyer", "stage": "matched"}
    first = FollowUpAgent().create_draft(lead, 1)
    second = FollowUpAgent().create_draft(lead, 1)
    assert first["status"] == "draft_only"
    assert second["status"] == "already_created"
    assert len(calls) == 1
    assert first["sent"] is False


def test_followup_refuses_terminal_leads_and_bad_attempts():
    agent = FollowUpAgent()
    assert agent.create_draft({"id": 2, "email": "a@b.com", "stage": "won"})["status"] == "terminal_lead"
    assert agent.create_draft({"id": 2, "email": "a@b.com"}, 0)["status"] == "invalid_attempt"
