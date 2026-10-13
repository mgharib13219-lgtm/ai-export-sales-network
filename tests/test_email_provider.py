from types import SimpleNamespace

from app import providers


class FakeSMTP:
    sent = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        assert user == "sales@example.com"
        assert password == "test-password"

    def send_message(self, message):
        self.sent.append(message)


def test_smtp_provider_sends_email_over_starttls(monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setattr(providers, "settings", SimpleNamespace(
        email_provider="smtp", smtp_host="smtp.example.com", smtp_port=587,
        smtp_user="sales@example.com", smtp_password="test-password"
    ))
    monkeypatch.setattr(providers.smtplib, "SMTP", FakeSMTP)

    result = providers.EmailProvider().send("buyer@example.org", "Product inquiry", "Hello buyer")

    assert result["status"] == "sent"
    assert result["to"] == "buyer@example.org"
    assert len(FakeSMTP.sent) == 1
    assert FakeSMTP.sent[0]["Subject"] == "Product inquiry"
    assert FakeSMTP.sent[0].get_content().strip() == "Hello buyer"


def test_email_provider_stays_draft_only_without_smtp_configuration(monkeypatch):
    monkeypatch.setattr(providers, "settings", SimpleNamespace(
        email_provider="none", smtp_host="", smtp_port=587,
        smtp_user="", smtp_password=""
    ))

    result = providers.EmailProvider().send("buyer@example.org", "Subject", "Body")

    assert result["status"] == "draft_only"
    assert result["body"] == "Body"


def test_smtp_failure_does_not_expose_exception_details(monkeypatch):
    class BrokenSMTP(FakeSMTP):
        def login(self, user, password):
            raise RuntimeError("secret-password-from-provider")

    monkeypatch.setattr(providers, "settings", SimpleNamespace(
        email_provider="smtp", smtp_host="smtp.example.com", smtp_port=587,
        smtp_user="sales@example.com", smtp_password="test-password"
    ))
    monkeypatch.setattr(providers.smtplib, "SMTP", BrokenSMTP)

    result = providers.EmailProvider().send("buyer@example.org", "Subject", "Body")

    assert result["status"] == "send_failed"
    assert "secret-password-from-provider" not in str(result)
