from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.marketplace_ui import router


def test_public_marketplace_page_is_available_and_has_safe_dom_rendering():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/market")
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "بازار تجارت جهانی" in response.text
    assert "textContent" in response.text
    assert "innerHTML" not in response.text
    assert "sessionStorage" in response.text
