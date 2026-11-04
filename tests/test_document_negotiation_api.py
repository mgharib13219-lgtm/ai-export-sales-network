import json
from fastapi.testclient import TestClient
import app.main as main


def test_document_upload_endpoint_extracts_in_memory_and_never_verifies(monkeypatch):
    main.app.dependency_overrides[main.require_admin] = lambda: True
    try:
        client = TestClient(main.app)
        response = client.post(
            "/crm/documents/extract",
            files={"file": ("supplier.txt", b"Supplier contact: trade@example.com", "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "extracted"
        assert data["stored"] is False
        assert data["authenticity_verified"] is False
        assert "trade@example.com" in data["extracted_fields"]["emails"]
    finally:
        main.app.dependency_overrides.pop(main.require_admin, None)


def test_negotiation_outcome_is_recorded_and_aggregate_learning_is_anonymized(monkeypatch):
    main.app.dependency_overrides[main.require_admin] = lambda: True
    monkeypatch.setattr(main, "get_lead", lambda lead_id: {"id": lead_id, "stage": "negotiation"})
    activities = []
    monkeypatch.setattr(main, "add_activity", lambda *args: activities.append(args) or 44)
    monkeypatch.setattr(main, "add_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "list_leads", lambda limit=500: [{"id": 3}])
    monkeypatch.setattr(main, "list_activities", lambda lead_id, limit=100: [
        {"kind": "negotiation_outcome", "body": json.dumps({
            "outcome": "won", "accepted_unit_price": 9.5, "currency": "EUR",
            "incoterm": "FCA", "payment_terms": "advance"
        })},
        {"kind": "negotiation_outcome", "body": json.dumps({
            "outcome": "won", "accepted_unit_price": 10.5, "currency": "EUR",
            "incoterm": "FCA", "payment_terms": "advance"
        })},
        {"kind": "negotiation_outcome", "body": json.dumps({
            "outcome": "lost", "currency": "EUR", "incoterm": "FCA",
            "payment_terms": "advance"
        })},
    ])
    try:
        client = TestClient(main.app)
        response = client.post("/crm/leads/3/negotiation-outcome", json={
            "outcome": "won", "accepted_unit_price": 9.5, "currency": "EUR",
            "incoterm": "FCA", "payment_terms": "advance"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "recorded"
        summary = client.get("/crm/negotiation/learning")
        assert summary.status_code == 200
        result = summary.json()
        assert result["segments"][0]["sample_size"] == 3
        assert "buyer" not in result["segments"][0]
        assert result["automatic_price_adjustment"] is False
    finally:
        main.app.dependency_overrides.pop(main.require_admin, None)
