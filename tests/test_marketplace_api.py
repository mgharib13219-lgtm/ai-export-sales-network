import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.marketplace as marketplace


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "marketplace-test.sqlite3"

    def connect():
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    monkeypatch.setattr(marketplace, "_con", connect)
    monkeypatch.setattr(marketplace, "add_audit_event", lambda *args, **kwargs: None)
    marketplace.init_marketplace()
    app = FastAPI()
    app.include_router(marketplace.router)
    return TestClient(app)


def _register_and_login(client, role, email):
    response = client.post("/marketplace/register", json={
        "email": email, "company_name": email.split("@")[0] + " Ltd",
        "country": "Germany", "role": role, "password": "a-long-test-password"
    })
    assert response.status_code == 200
    login = client.post("/marketplace/login", json={
        "email": email, "password": "a-long-test-password"
    })
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def test_buyer_supplier_discovery_and_ownership_lifecycle(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller_headers = _register_and_login(client, "producer", "seller@example.com")
    buyer_headers = _register_and_login(client, "buyer", "buyer@example.com")

    product = {
        "name": "Seedless golden raisins", "category": "dried fruit",
        "description": "Grade A seedless golden raisins", "origin": "Türkiye",
        "capacity": "20 tonnes monthly", "moq": "1 tonne", "target_markets": "Germany"
    }
    created_product = client.post("/marketplace/products", json=product, headers=seller_headers)
    assert created_product.status_code == 200
    product_id = created_product.json()["product_id"]

    request = {
        "title": "Golden raisins", "category": "dried fruit",
        "specification": "seedless golden raisins grade A",
        "destination": "Germany", "quantity": "10 tonnes"
    }
    created_request = client.post("/marketplace/requests", json=request, headers=buyer_headers)
    assert created_request.status_code == 200
    request_id = created_request.json()["request_id"]

    matches = client.get(f"/marketplace/matches/requests/{request_id}", headers=seller_headers)
    assert matches.status_code == 200
    assert matches.json()["matches"][0]["listing_id"] == product_id
    assert matches.json()["matches"][0]["automatically_cleared"] is False

    assert client.patch(f"/marketplace/products/{product_id}", json=product,
                        headers=buyer_headers).status_code == 403
    assert client.patch(f"/marketplace/requests/{request_id}", json=request,
                        headers=seller_headers).status_code == 403

    updated_product = {**product, "capacity": "30 tonnes monthly"}
    assert client.patch(f"/marketplace/products/{product_id}", json=updated_product,
                        headers=seller_headers).status_code == 200
    assert client.delete(f"/marketplace/products/{product_id}", headers=seller_headers).status_code == 200
    assert all(item["id"] != product_id for item in client.get("/marketplace/products").json())

    updated_request = {**request, "quantity": "12 tonnes"}
    assert client.patch(f"/marketplace/requests/{request_id}", json=updated_request,
                        headers=buyer_headers).status_code == 200

    assert client.post("/marketplace/logout", headers=seller_headers).status_code == 200
    assert client.get("/marketplace/me", headers=seller_headers).status_code == 401


def test_closed_requests_are_not_shown_to_producers(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller_headers = _register_and_login(client, "producer", "seller2@example.com")
    buyer_headers = _register_and_login(client, "buyer", "buyer2@example.com")
    request = {
        "title": "Industrial fasteners", "category": "components",
        "specification": "stainless steel bolts", "destination": "France"
    }
    created = client.post("/marketplace/requests", json=request, headers=buyer_headers)
    request_id = created.json()["request_id"]
    closed = client.delete(f"/marketplace/requests/{request_id}", headers=buyer_headers)
    assert closed.status_code == 200
    feed = client.get("/marketplace/requests", headers=seller_headers)
    assert feed.status_code == 200
    assert all(item["id"] != request_id for item in feed.json())

def test_login_throttles_repeated_invalid_passwords(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _register_and_login(client, "buyer", "throttle@example.com")
    for _ in range(5):
        response = client.post("/marketplace/login", json={
            "email": "throttle@example.com", "password": "incorrect-password"
        })
        assert response.status_code == 401
    locked = client.post("/marketplace/login", json={
        "email": "throttle@example.com", "password": "a-long-test-password"
    })
    assert locked.status_code == 429
