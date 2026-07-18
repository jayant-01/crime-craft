"""Smoke test — guards against 'the app doesn't even start' regressions.

If this fails, nothing else matters. Always run first in CI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_app_boots_and_health_is_ok():
    """If imports break or middleware mis-wires, this is the first thing to fail."""
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "env" in body
    assert "catalyst" in body


def test_openapi_schema_renders():
    """The auto-generated OpenAPI doc rendering is a useful belt-and-suspenders
    check — it catches typing errors in route signatures and missing response models."""
    client = TestClient(app)
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})
    # Spot-check that the headline endpoints from the demo script all registered
    # (now under the /api prefix — the SPA owns the root paths).
    for required in ("/api/chat", "/api/cases", "/api/analytics/trends",
                     "/api/predictive/recidivism", "/api/network/case/{case_id}"):
        assert required in paths, f"missing route in OpenAPI: {required}"
