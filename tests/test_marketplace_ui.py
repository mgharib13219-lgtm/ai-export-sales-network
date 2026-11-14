import re
import shutil
import subprocess

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
    assert response.headers["cache-control"] == "no-store"
    assert "بازار تجارت جهانی" in response.text
    assert "href=\"/trade/workspace\"" in response.text
    assert "textContent" in response.text
    assert "innerHTML" not in response.text
    assert "sessionStorage" in response.text
    assert "changePassword" in response.text
    assert "/marketplace/password" in response.text
    # These handlers use await and must remain async or the browser rejects
    # the entire inline script before any marketplace control can run.
    assert "async function register()" in response.text
    assert "async function discoverBuyers()" in response.text
    # A bare `async` expression is valid JavaScript syntax but throws at runtime,
    # aborting the rest of the page script and leaving every control inactive.
    assert not re.search(r"(?m)^\s*async\s*$", response.text)



def test_marketplace_inline_javascript_parses_when_node_is_available():
    if not shutil.which("node"):
        return
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/market")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", response.text, re.DOTALL)
    assert scripts, "marketplace page must include its application script"
    for script in scripts:
        checked = subprocess.run(
            ["node", "--check"], input=script, text=True,
            capture_output=True, timeout=15
        )
        assert checked.returncode == 0, checked.stderr
