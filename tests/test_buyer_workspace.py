import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.marketplace as marketplace


def _client(tmp_path, monkeypatch):
    path = tmp_path / "buyer-workspace.sqlite3"

    def connect():
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    monkeypatch.setattr(marketplace, "_con", connect)
    monkeypatch.setattr(marketplace, "add_audit_event", lambda *a, **k: None)
    marketplace.init_marketplace()
    app = FastAPI()
    app.include_router(marketplace.router)
    return TestClient(app)


def _account(client, email, role):
    client.post("/marketplace/register", json={
        "email": email, "company_name": email.split("@")[0] + " Ltd",
        "country": "Germany", "role": role, "password": "a-long-test-password"
    })
    response = client.post("/marketplace/login", json={
        "email": email, "password": "a-long-test-password"
    })
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_buyer_workspace_returns_own_requests_and_public_matches(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    buyer = _account(client, "buyer@example.com", "buyer")
    seller = _account(client, "seller@example.com", "producer")
    client.post("/marketplace/products", headers=seller, json={
        "name": "Golden raisins", "category": "dried fruit",
        "description": "Golden raisins, export quality, packed in cartons.",
        "origin": "Türkiye", "capacity": "20 tonnes/month", "moq": "1 tonne"
    })
    client.post("/marketplace/requests", headers=buyer, json={
        "title": "Golden raisins", "category": "dried fruit",
        "specification": "Golden raisins export quality in cartons.",
        "destination": "Germany", "quantity": "10 tonnes", "share_contact": True
    })
    response = client.get("/marketplace/requests/mine", headers=buyer)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1 and len(payload[0]["matches"]) == 1
    match = payload[0]["matches"][0]
    assert match["supplier_company"] == "seller Ltd"
    assert match["score"] > 0
    assert "buyer_email" not in match and "supplier_email" not in match
    assert client.get("/marketplace/requests/mine", headers=seller).status_code == 403


def test_buyer_workspace_page_is_registered():
    from app.buyer_workspace_ui import router
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/buyer/workspace")
    assert response.status_code == 200
    assert 'id="requestList"' in response.text
    assert 'id="langToggle"' in response.text
    assert "Buyer workspace" in response.text
    assert "buyer_workspace_lang" in response.text
    assert response.headers["x-frame-options"] == "DENY"


def test_buyer_workspace_inline_javascript_parses_when_node_is_available():
    import re
    import shutil
    import subprocess

    if not shutil.which("node"):
        return
    from app.buyer_workspace_ui import router
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/buyer/workspace")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", response.text, re.DOTALL)
    assert scripts, "buyer workspace must include its application script"
    for script in scripts:
        checked = subprocess.run(
            ["node", "--check"], input=script, text=True,
            capture_output=True, timeout=15
        )
        assert checked.returncode == 0, checked.stderr
