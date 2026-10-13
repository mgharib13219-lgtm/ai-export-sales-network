from fastapi import HTTPException
import pytest

from app import main


class FakeEmailProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def send(self, to, subject, body):
        self.calls.append((to, subject, body))
        return dict(self.result)


def setup_lead(monkeypatch, email="buyer@example.org", stage="matched"):
    monkeypatch.setattr(main, "get_lead", lambda lead_id: {
        "id": lead_id, "email": email, "stage": stage, "company_name": "Buyer Co"
    })
    monkeypatch.setattr(main, "add_activity", lambda *args: 41)
    monkeypatch.setattr(main, "add_audit_event", lambda *args, **kwargs: None)


def test_outbound_email_requires_human_approval(monkeypatch):
    setup_lead(monkeypatch)
    monkeypatch.setattr(main, "email_provider", FakeEmailProvider({"status": "sent"}))

    with pytest.raises(HTTPException) as exc:
        main.crm_send_email(7, main.EmailSendRequest(
            subject="Product details", body="Hello", approval_confirmed=False
        ))

    assert exc.value.status_code == 400
    assert exc.value.detail == "human_approval_required"


def test_outbound_email_requires_buyer_email(monkeypatch):
    setup_lead(monkeypatch, email="")
    monkeypatch.setattr(main, "email_provider", FakeEmailProvider({"status": "sent"}))

    with pytest.raises(HTTPException) as exc:
        main.crm_send_email(7, main.EmailSendRequest(
            subject="Product details", body="Hello", approval_confirmed=True
        ))

    assert exc.value.detail == "valid_buyer_email_required"


def test_outbound_email_records_human_approved_send_result(monkeypatch):
    setup_lead(monkeypatch)
    provider = FakeEmailProvider({"status": "sent", "to": "buyer@example.org", "subject": "Product details"})
    monkeypatch.setattr(main, "email_provider", provider)

    result = main.crm_send_email(7, main.EmailSendRequest(
        subject="Product details", body="Hello", approval_confirmed=True
    ))

    assert result["status"] == "sent"
    assert result["activity_id"] == 41
    assert result["human_approved"] is True
    assert provider.calls == [("buyer@example.org", "Product details", "Hello")]
