from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_operations_ui import router


def test_admin_operations_page_is_registered_and_hardened():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/admin/operations")
    assert response.status_code == 200
    assert 'id="dealList"' in response.text
    assert 'id="auditList"' in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
