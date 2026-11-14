"""Synthetic end-to-end acceptance journey for the marketplace MVP.

All records are isolated in a temporary SQLite database. No external services,
real contacts, email delivery, or production data are used.
"""
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.marketplace as marketplace
import app.trade_workspace as trade
from app.auth import require_admin


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "e2e-acceptance.sqlite3"

    def connect():
        con = sqlite3.connect(db_path)
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


def _account(client, *, email, role):
    registered = client.post("/marketplace/register", json={
        "email": email,
        "company_name": f"Synthetic {role.title()} Ltd",
        "country": "Germany",
        "role": role,
        "password": "synthetic-e2e-password-2026",
    })
    assert registered.status_code == 200, registered.text
    logged_in = client.post("/marketplace/login", json={
        "email": email,
        "password": "synthetic-e2e-password-2026",
    })
    assert logged_in.status_code == 200, logged_in.text
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def test_synthetic_seller_to_buyer_acceptance_journey(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    # 1. Separate seller and buyer identities and authenticated sessions.
    seller = _account(client, email="synthetic-seller@example.invalid", role="producer")
    buyer = _account(client, email="synthetic-buyer@example.invalid", role="buyer")

    # 2. Seller records a synthetic product listing and an independent inventory item.
    listing_response = client.post("/marketplace/products", headers=seller, json={
        "name": "Synthetic golden raisins",
        "category": "dried fruit",
        "description": "Synthetic test listing: seedless golden raisins grade A",
        "origin": "Takestan, Iran (test data only)",
        "capacity": "20 tonnes (test assumption only)",
        "moq": "1 tonne (test assumption only)",
        "target_markets": "Kazakhstan (test scenario only)",
    })
    assert listing_response.status_code == 200, listing_response.text
    listing_id = listing_response.json()["product_id"]

    inventory_response = client.post("/trade/inventory", headers=seller, json={
        "sku": "SYN-RAISIN-001",
        "product_name": "Synthetic golden raisins",
        "warehouse_country": "Iran",
        "quantity": 20,
        "unit": "tonne",
    })
    assert inventory_response.status_code == 200, inventory_response.text
    inventory_id = inventory_response.json()["inventory_id"]

    # 3. Seller creates and publishes a clearly synthetic price-list draft.
    price_list = client.post("/trade/price-lists", headers=seller, json={
        "name": "Synthetic acceptance-test price list",
        "currency": "EUR",
    })
    assert price_list.status_code == 200, price_list.text
    price_list_id = price_list.json()["price_list_id"]
    price_item = client.post(f"/trade/price-lists/{price_list_id}/items",
        headers=seller, json={
            "product_name": "Synthetic golden raisins",
            "unit": "tonne",
            "unit_price": 1000,
            "minimum_quantity": 1,
            "incoterm": "EXW",
            "destination_country": "Kazakhstan",
        })
    assert price_item.status_code == 200, price_item.text
    published = client.post(f"/trade/price-lists/{price_list_id}/publish", headers=seller)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"

    # 4. Public catalogue exposes the listing, without requiring a login.
    public_catalogue = client.get("/marketplace/products")
    assert public_catalogue.status_code == 200
    assert any(row["id"] == listing_id for row in public_catalogue.json())

    # 5. Buyer submits a synthetic sourcing request.
    request_response = client.post("/marketplace/requests", headers=buyer, json={
        "title": "Synthetic golden raisins sourcing request",
        "category": "dried fruit",
        "specification": "Seedless golden raisins grade A, synthetic test only",
        "destination": "Kazakhstan",
        "quantity": "10 tonnes (test assumption only)",
    })
    assert request_response.status_code == 200, request_response.text
    request_id = request_response.json()["request_id"]

    # 6. Supplier sees the open request and can retrieve ranked candidates.
    supplier_feed = client.get("/marketplace/requests", headers=seller)
    assert supplier_feed.status_code == 200
    assert any(row["id"] == request_id for row in supplier_feed.json())

    matches = client.get(f"/marketplace/matches/requests/{request_id}", headers=seller)
    assert matches.status_code == 200, matches.text
    assert matches.json()["matches"]
    assert matches.json()["matches"][0]["listing_id"] == listing_id
    assert matches.json()["matches"][0]["automatically_cleared"] is False
    assert "unverified" in matches.json()["note"].lower()

    # 7. Buyer sees its own request and candidate matches.
    buyer_workspace = client.get("/marketplace/requests/mine", headers=buyer)
    assert buyer_workspace.status_code == 200
    own_request = next(row for row in buyer_workspace.json() if row["id"] == request_id)
    assert own_request["matches"]
    assert own_request["matches"][0]["listing_id"] == listing_id
    assert own_request["matches"][0]["automatically_cleared"] is False

    # 8. Tenant/role boundaries prevent cross-editing.
    assert client.patch(f"/marketplace/products/{listing_id}", headers=buyer, json={
        "name": "Unauthorized edit",
        "category": "dried fruit",
        "description": "Should not be accepted",
        "origin": "Germany",
    }).status_code == 403
    assert client.patch(f"/marketplace/requests/{request_id}", headers=seller, json={
        "title": "Unauthorized edit",
        "category": "dried fruit",
        "specification": "Should not be accepted",
        "destination": "Kazakhstan",
    }).status_code == 403

    # 9. Seller inventory and price list remain scoped to the seller account.
    seller_inventory = client.get("/trade/inventory", headers=seller)
    assert seller_inventory.status_code == 200
    assert any(row["id"] == inventory_id for row in seller_inventory.json())
    seller_price_lists = client.get("/trade/price-lists", headers=seller)
    assert seller_price_lists.status_code == 200
    assert any(row["id"] == price_list_id for row in seller_price_lists.json())

    # 10. Buyer cannot access seller-only inventory operations.
    assert client.get("/trade/inventory", headers=buyer).status_code == 403
