import hashlib
import hmac
import json
import sqlite3
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

import app.marketplace as marketplace
import app.subscriptions as subscriptions
import app.buyer_discovery as buyer_discovery
from app.auth import require_admin


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "marketplace-entitlements.sqlite3"

    def connect():
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    monkeypatch.setattr(marketplace, "_con", connect)
    monkeypatch.setattr(subscriptions, "_con", connect)
    monkeypatch.setattr(buyer_discovery, "_con", connect)
    monkeypatch.setattr(marketplace, "add_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(subscriptions, "add_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(buyer_discovery, "add_audit_event", lambda *args, **kwargs: None)
    marketplace.init_marketplace()
    subscriptions.init_subscriptions()
    buyer_discovery.init_buyer_discovery()

    app = FastAPI()
    app.include_router(marketplace.router)
    app.include_router(subscriptions.router)
    app.include_router(buyer_discovery.router)

    def admin_override(request: Request):
        if request.headers.get("x-admin-token") != "test-admin-token":
            raise HTTPException(status_code=401, detail="Unauthorized")
        return True

    app.dependency_overrides[require_admin] = admin_override
    return TestClient(app)


def _register(client, email, role):
    response = client.post("/marketplace/register", json={
        "email": email, "company_name": email.split("@")[0].title() + " Ltd",
        "country": "Germany", "role": role, "password": "a-long-test-password"
    })
    assert response.status_code == 200
    login = client.post("/marketplace/login", json={
        "email": email, "password": "a-long-test-password"
    })
    assert login.status_code == 200
    return response.json()["user_id"], {"Authorization": "Bearer " + login.json()["access_token"]}


def _grant(client, user_id, plan):
    return client.post(f"/marketplace/subscription/users/{user_id}", json={
        "plan_code": plan, "duration_days": 30
    }, headers={"x-admin-token": "test-admin-token"})


def test_lead_details_are_plan_gated_and_contact_requires_buyer_opt_in(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, buyer_headers = _register(client, "buyer@example.com", "buyer")
    buyer_request = client.post("/marketplace/requests", headers=buyer_headers, json={
        "title": "Industrial pump", "category": "machinery",
        "specification": "High pressure stainless steel pump with ATEX documentation",
        "destination": "Germany", "quantity": "25 units", "share_contact": True
    })
    assert buyer_request.status_code == 200

    supplier_id, supplier_headers = _register(client, "supplier@example.com", "producer")
    free_view = client.get("/marketplace/requests", headers=supplier_headers).json()
    assert isinstance(free_view, list)
    assert "specification" not in free_view[0]
    assert "buyer_email" not in free_view[0]

    assert _grant(client, supplier_id, "growth").status_code == 200
    growth_view = client.get("/marketplace/requests", headers=supplier_headers).json()
    assert "ATEX documentation" in growth_view[0]["specification"]
    assert "buyer_email" not in growth_view[0]

    assert _grant(client, supplier_id, "premium").status_code == 200
    premium_view = client.get("/marketplace/requests", headers=supplier_headers).json()
    assert premium_view[0]["buyer_email"] == "buyer@example.com"


def test_buyer_contact_is_hidden_when_buyer_did_not_opt_in(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, buyer_headers = _register(client, "privatebuyer@example.com", "buyer")
    client.post("/marketplace/requests", headers=buyer_headers, json={
        "title": "Packaging materials", "category": "packaging",
        "specification": "Food-safe recyclable packaging with custom printing",
        "destination": "France", "share_contact": False
    })
    supplier_id, supplier_headers = _register(client, "premium@example.com", "producer")
    assert _grant(client, supplier_id, "premium").status_code == 200
    view = client.get("/marketplace/requests", headers=supplier_headers).json()
    assert view[0]["buyer_email"] is None
    assert view[0]["buyer_company"] is None


def test_monthly_agent_credits_are_reserved_atomically_and_enforced(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    supplier_id, _ = _register(client, "credits@example.com", "producer")
    assert _grant(client, supplier_id, "starter").status_code == 200
    for expected in range(4, -1, -1):
        usage = subscriptions.reserve_agent_credit(supplier_id)
        assert usage["remaining"] == expected
    with pytest.raises(HTTPException) as exc:
        subscriptions.reserve_agent_credit(supplier_id)
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "agent_monthly_credits_exhausted"


def test_buyer_discovery_saves_provenance_and_requires_manual_review(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    supplier_id, headers = _register(client, "research@example.com", "producer")
    assert _grant(client, supplier_id, "starter").status_code == 200
    monkeypatch.setattr(buyer_discovery, "settings", SimpleNamespace(
        search_provider="serpapi", search_api_key="test-key"))
    monkeypatch.setattr(buyer_discovery, "_safe_public_url", lambda url: url.startswith("https://"))
    monkeypatch.setattr(buyer_discovery.search_provider, "search_buyers", lambda query, country: [
        {"title": "Example Industrial Importer", "url": "https://example.org/imports",
         "snippet": "Importer of industrial pumps", "source": "google"}
    ])
    response = client.post("/marketplace/agent/buyer-discovery", headers=headers, json={
        "product_terms": "industrial pumps", "target_country": "Germany"
    })
    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["review_status"] == "needs_supplier_review"
    assert response.json()["credits"]["used"] == 1
    saved = client.get("/marketplace/agent/buyer-candidates", headers=headers).json()
    assert saved[0]["source_type"] == "public_search_result"
    assert saved[0]["collection_basis"] == "public_search_snippet"
    assert "email" not in saved[0]
    reviewed = client.patch("/marketplace/agent/buyer-candidates/" + str(candidate["id"]),
                            headers=headers, json={"relevant": True, "note": "Checked manually"})
    assert reviewed.status_code == 200
    assert "does not establish permission to contact" in reviewed.json()["note"]


def test_failed_buyer_search_refunds_reserved_credit(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    supplier_id, headers = _register(client, "searchfail@example.com", "producer")
    assert _grant(client, supplier_id, "starter").status_code == 200
    monkeypatch.setattr(buyer_discovery, "settings", SimpleNamespace(
        search_provider="serpapi", search_api_key="test-key"))
    monkeypatch.setattr(buyer_discovery.search_provider, "search_buyers",
                        lambda *args: (_ for _ in ()).throw(RuntimeError("provider unavailable")))
    response = client.post("/marketplace/agent/buyer-discovery", headers=headers, json={
        "product_terms": "industrial pumps", "target_country": "Germany"
    })
    assert response.status_code == 502
    assert client.get("/marketplace/subscription/credits", headers=headers).json()["used"] == 0


def test_upgrade_request_is_idempotent_and_does_not_activate_plan(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    supplier_id, headers = _register(client, "upgrade@example.com", "producer")
    first = client.post("/marketplace/subscription/upgrade-requests", headers=headers,
                        json={"plan_code": "growth", "note": "Need more buyer leads"})
    second = client.post("/marketplace/subscription/upgrade-requests", headers=headers,
                         json={"plan_code": "growth", "note": "Duplicate click"})
    assert first.status_code == second.status_code == 200
    assert first.json()["request_id"] == second.json()["request_id"]
    assert client.get("/marketplace/subscription/me", headers=headers).json()["plan_code"] == "free"
    pending = client.get("/marketplace/subscription/upgrade-requests",
                         headers={"x-admin-token": "test-admin-token"})
    assert pending.status_code == 200
    assert pending.json()[0]["user_id"] == supplier_id


def test_stripe_signature_rejects_tampering_and_accepts_valid_payload(monkeypatch):
    secret = "whsec_test_secret"
    monkeypatch.setattr(subscriptions, "settings", SimpleNamespace(stripe_webhook_secret=secret))
    payload = json.dumps({"id": "evt_test", "type": "noop"}).encode()
    timestamp = int(time.time())
    signed = str(timestamp).encode() + b"." + payload
    signature = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={signature}"
    assert subscriptions._verify_stripe_signature(payload, header)
    assert not subscriptions._verify_stripe_signature(payload + b" ", header)
    assert not subscriptions._verify_stripe_signature(payload, f"t={timestamp-900},v1={signature}")


def test_checkout_is_closed_when_provider_and_transparent_price_are_not_configured(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, headers = _register(client, "billing@example.com", "producer")
    monkeypatch.setattr(subscriptions, "settings", SimpleNamespace(
        stripe_secret_key="", stripe_webhook_secret="", billing_success_url="",
        billing_cancel_url="", stripe_price_id_starter="", stripe_price_display_starter=""))
    response = client.post("/marketplace/subscription/billing/checkout?plan_code=starter",
                           headers=headers)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "billing_not_configured"


def test_signed_stripe_checkout_webhook_activates_subscription_once(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    user_id, headers = _register(client, "paid@example.com", "producer")
    secret = "whsec_checkout_test"
    monkeypatch.setattr(subscriptions, "settings", SimpleNamespace(stripe_webhook_secret=secret))
    future = (subscriptions.datetime.now(subscriptions.timezone.utc) +
              subscriptions.timedelta(days=30)).isoformat()
    monkeypatch.setattr(subscriptions, "_stripe_subscription_snapshot", lambda sub_id, plan: {
        "id": sub_id, "status": "active", "ends_at": future, "customer": "cus_test"
    })
    event = {
        "id": "evt_checkout_test_001", "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test", "client_reference_id": str(user_id),
            "metadata": {"user_id": str(user_id), "plan_code": "starter"},
            "mode": "subscription", "payment_status": "paid", "subscription": "sub_test_001"
        }}
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    timestamp = int(time.time())
    signed = str(timestamp).encode() + b"." + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    headers_sig = {"stripe-signature": f"t={timestamp},v1={digest}"}
    first = client.post("/marketplace/subscription/billing/webhook", content=payload,
                        headers=headers_sig)
    assert first.status_code == 200
    assert first.json()["activated"] is True
    current = client.get("/marketplace/subscription/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["plan_code"] == "starter"
    assert current.json()["billing_provider"] == "stripe"
    duplicate = client.post("/marketplace/subscription/billing/webhook", content=payload,
                            headers=headers_sig)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True


def test_stripe_billing_portal_requires_a_stripe_subscription(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, headers = _register(client, "manualgrant@example.com", "producer")
    monkeypatch.setattr(subscriptions, "settings", SimpleNamespace(
        stripe_secret_key="sk_test", billing_success_url="https://app.example/billing/return"))
    response = client.post("/marketplace/subscription/billing/portal", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "stripe_subscription_not_found"
