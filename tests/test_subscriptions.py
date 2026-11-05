import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.marketplace as marketplace
import app.subscriptions as subscriptions
from app.auth import require_admin


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "subscription-test.sqlite3"

    def connect():
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    monkeypatch.setattr(marketplace, "_con", connect)
    monkeypatch.setattr(subscriptions, "_con", connect)
    monkeypatch.setattr(marketplace, "add_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(subscriptions, "add_audit_event", lambda *args, **kwargs: None)
    marketplace.init_marketplace()
    subscriptions.init_subscriptions()

    app = FastAPI()
    app.include_router(marketplace.router)
    app.include_router(subscriptions.router)
    app.dependency_overrides[require_admin] = lambda: True
    return TestClient(app)


def _register(client, email="supplier@example.com"):
    response = client.post("/marketplace/register", json={
        "email": email, "company_name": "Supplier Ltd", "country": "Germany",
        "role": "producer", "password": "a-long-test-password"
    })
    assert response.status_code == 200
    user_id = response.json()["user_id"]
    login = client.post("/marketplace/login", json={
        "email": email, "password": "a-long-test-password"
    })
    return user_id, {"Authorization": "Bearer " + login.json()["access_token"]}


def _product(index):
    return {
        "name": f"Industrial component {index}", "category": "components",
        "description": "Precision manufactured industrial component",
        "origin": "Germany", "capacity": "1000 units monthly",
        "moq": "100 units", "target_markets": "EU"
    }


def test_plan_catalog_and_free_subscription_are_available(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    user_id, headers = _register(client)
    plans = client.get("/marketplace/subscription/plans")
    assert plans.status_code == 200
    assert {p["code"] for p in plans.json()["plans"]} == {"free", "starter", "growth", "premium"}
    current = client.get("/marketplace/subscription/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["plan_code"] == "free"
    assert current.json()["entitlements"]["published_listing_limit"] == 3


def test_free_listing_quota_is_enforced_server_side(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, headers = _register(client)
    for index in range(1, 4):
        assert client.post("/marketplace/products", json=_product(index), headers=headers).status_code == 200
    blocked = client.post("/marketplace/products", json=_product(4), headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "subscription_listing_limit_reached"


def test_operator_granted_plan_changes_quota_and_user_cannot_grant_self(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    user_id, headers = _register(client)
    # Paid plans cannot be self-activated by a supplier.
    assert client.post(f"/marketplace/subscription/users/{user_id}", json={
        "plan_code": "starter", "duration_days": 30
    }, headers=headers).status_code == 403

    grant = client.post(f"/marketplace/subscription/users/{user_id}", json={
        "plan_code": "starter", "duration_days": 30,
        "external_reference": "manual-review-ticket-123"
    })
    assert grant.status_code == 200
    assert grant.json()["plan_code"] == "starter"

    for index in range(1, 5):
        assert client.post("/marketplace/products", json=_product(index), headers=headers).status_code == 200
    assert client.get("/marketplace/subscription/me", headers=headers).json()["plan_code"] == "starter"


def test_subscription_revocation_returns_supplier_to_free_entitlement(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    user_id, headers = _register(client)
    client.post(f"/marketplace/subscription/users/{user_id}", json={
        "plan_code": "growth", "duration_days": 30
    })
    revoked = client.delete(f"/marketplace/subscription/users/{user_id}")
    assert revoked.status_code == 200
    assert client.get("/marketplace/subscription/me", headers=headers).json()["plan_code"] == "free"
