import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.marketplace as marketplace
import app.trade_workspace as trade
from app.auth import require_admin


def _client(tmp_path, monkeypatch):
    path = tmp_path / "trade-workspace.sqlite3"

    def connect():
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    monkeypatch.setattr(marketplace, "_con", connect)
    monkeypatch.setattr(trade, "_con", connect)
    monkeypatch.setattr(marketplace, "add_audit_event", lambda *a, **k: None)
    monkeypatch.setattr(trade, "add_audit_event", lambda *a, **k: None)
    marketplace.init_marketplace()
    trade.init_trade_workspace()
    app = FastAPI()
    app.include_router(marketplace.router)
    app.include_router(trade.router)
    app.dependency_overrides[require_admin] = lambda: True
    return TestClient(app)


def _account(client, email, role="producer"):
    client.post("/marketplace/register", json={
        "email": email, "company_name": email.split("@")[0] + " Ltd",
        "country": "Germany", "role": role, "password": "a-long-test-password"
    })
    response = client.post("/marketplace/login", json={
        "email": email, "password": "a-long-test-password"
    })
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_inventory_is_scoped_to_owning_producer(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller_a = _account(client, "a@example.com")
    seller_b = _account(client, "b@example.com")
    buyer = _account(client, "buyer@example.com", "buyer")

    created = client.post("/trade/inventory", headers=seller_a, json={
        "sku": "RAISIN-001", "product_name": "Golden raisins",
        "warehouse_country": "Türkiye", "quantity": 1200, "unit": "kg"
    })
    assert created.status_code == 200
    assert len(client.get("/trade/inventory", headers=seller_a).json()) == 1
    assert client.get("/trade/inventory", headers=seller_b).json() == []
    assert client.get("/trade/inventory", headers=buyer).status_code == 403
    assert client.post("/trade/inventory", headers=seller_b, json={
        "sku": "RAISIN-001", "product_name": "Other raisins",
        "warehouse_country": "Germany", "quantity": 10, "unit": "kg"
    }).status_code == 200


def test_inventory_quantity_cannot_be_negative_or_below_reservations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller = _account(client, "stock@example.com")
    created = client.post("/trade/inventory", headers=seller, json={
        "sku": "SKU-1", "product_name": "Olive oil",
        "warehouse_country": "Greece", "quantity": 100, "unit": "litre"
    })
    item_id = created.json()["inventory_id"]
    assert client.patch(f"/trade/inventory/{item_id}/quantity", headers=seller,
                        json={"quantity": -1}).status_code == 422
    assert client.patch(f"/trade/inventory/{item_id}/quantity", headers=seller,
                        json={"quantity": 0}).status_code == 200


def test_price_list_requires_item_before_publish_and_is_tenant_scoped(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller_a = _account(client, "prices-a@example.com")
    seller_b = _account(client, "prices-b@example.com")
    created = client.post("/trade/price-lists", headers=seller_a, json={
        "name": "EU wholesale November", "currency": "eur",
        "valid_from": "2026-11-01", "valid_until": "2026-11-30"
    })
    list_id = created.json()["price_list_id"]
    assert client.post(f"/trade/price-lists/{list_id}/publish", headers=seller_a).status_code == 409
    assert client.post(f"/trade/price-lists/{list_id}/items", headers=seller_b, json={
        "product_name": "Golden raisins", "unit": "kg", "unit_price": 3.2
    }).status_code == 404
    item = client.post(f"/trade/price-lists/{list_id}/items", headers=seller_a, json={
        "product_name": "Golden raisins", "unit": "kg", "unit_price": 3.2,
        "minimum_quantity": 500, "incoterm": "FOB", "destination_country": "Germany"
    })
    assert item.status_code == 200
    assert client.post(f"/trade/price-lists/{list_id}/publish", headers=seller_a).json()["status"] == "published"
    listed = client.get("/trade/price-lists", headers=seller_a).json()
    assert listed[0]["currency"] == "EUR"
    assert listed[0]["items"][0]["unit_price"] == 3.2
    assert client.get("/trade/price-lists", headers=seller_b).json() == []


def test_price_list_date_range_must_be_ordered(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    seller = _account(client, "dates@example.com")
    response = client.post("/trade/price-lists", headers=seller, json={
        "name": "Invalid period", "currency": "USD",
        "valid_from": "2026-12-01", "valid_until": "2026-11-01"
    })
    assert response.status_code == 422
