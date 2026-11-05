from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.hs_catalog_ui import router


def test_hs_catalog_admin_page_is_hardened_and_explains_source_requirements():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/admin/hs-catalog")
    assert response.status_code == 200
    assert "import-csv" in response.text
    assert "منبع دقیق" in response.text
    assert "۲۵ مگابایت" in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "connect-src 'self'" in response.headers["content-security-policy"]
