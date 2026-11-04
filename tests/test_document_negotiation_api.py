import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from types import SimpleNamespace
import app.main as main


def test_document_upload_endpoint_extracts_in_memory_and_never_verifies(monkeypatch):
    main.app.dependency_overrides[main.require_admin] = lambda: True
    monkeypatch.setattr(main, "get_lead", lambda lead_id: {"id": lead_id})
    recorded = []
    monkeypatch.setattr(main, "add_activity", lambda *args: recorded.append(args) or 41)
    monkeypatch.setattr(main, "add_audit_event", lambda *args, **kwargs: None)
    try:
        client = TestClient(main.app)
        response = client.post(
            "/crm/documents/extract",
            data={"lead_id": "3"},
            files={"file": ("supplier.txt", b"Supplier contact: trade@example.com", "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "extracted"
        assert data["stored"] is False
        assert data["authenticity_verified"] is False
        assert data["malware_scan_performed"] is False
        assert data["workflow_status"] == "pending_human_review"
        assert "trade@example.com" in data["extracted_fields"]["emails"]
        assert recorded[0][1] == "document_evidence_uploaded"
        assert data["sha256"] in recorded[0][3]
        assert "trade@example.com" not in recorded[0][3]
    finally:
        main.app.dependency_overrides.pop(main.require_admin, None)


def test_document_approver_credential_is_separate_and_fail_closed(monkeypatch):
    monkeypatch.setattr(main, "settings", SimpleNamespace(agent_approver_token="separate-review-token"))
    with pytest.raises(HTTPException) as exc:
        main.require_document_approver("wrong-token")
    assert exc.value.status_code == 401
    assert main.require_document_approver("separate-review-token") is None
    monkeypatch.setattr(main, "settings", SimpleNamespace(agent_approver_token=""))
    with pytest.raises(HTTPException) as missing:
        main.require_document_approver("anything")
    assert missing.value.status_code == 503


def test_document_review_requires_registered_hash_and_records_auditable_decision(monkeypatch):
    main.app.dependency_overrides[main.require_admin] = lambda: True
    main.app.dependency_overrides[main.require_document_approver] = lambda: True
    lead = {"id": 3, "stage": "verified"}
    monkeypatch.setattr(main, "get_lead", lambda lead_id: lead if lead_id == 3 else None)
    sha = "a" * 64
    uploads = [{
        "kind": "document_evidence_uploaded",
        "body": json.dumps({"sha256": sha, "filename": "certificate.pdf"}),
    }]
    monkeypatch.setattr(main, "list_activities", lambda lead_id, limit=500: uploads)
    writes = []
    audits = []
    monkeypatch.setattr(main, "add_activity", lambda *args: writes.append(args) or 77)
    monkeypatch.setattr(main, "add_audit_event", lambda *args, **kwargs: audits.append((args, kwargs)))
    try:
        client = TestClient(main.app)
        missing = client.post(f"/crm/leads/3/documents/{'b' * 64}/review", json={
            "decision": "accepted_for_next_step",
            "reviewer_reference": "reviewer@example.com",
            "reason": "Original document visually checked against the supplied file.",
        })
        assert missing.status_code == 404
        response = client.post(f"/crm/leads/3/documents/{sha}/review", json={
            "decision": "accepted_for_next_step",
            "reviewer_reference": "reviewer@example.com",
            "reason": "Original document visually checked against the supplied file.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "review_recorded"
        assert data["reviewer_identity_verified"] is False
        assert data["authenticity_verified"] is False
        assert data["issuer_verified"] is False
        assert data["malware_scan_performed"] is False
        assert writes[0][1] == "document_evidence_review"
        assert audits[0][0][0] == "crm.document_evidence_reviewed"
        status = client.get(f"/crm/leads/3/documents/{sha}")
        assert status.status_code == 200
        assert status.json()["workflow_status"] == "pending_review"
    finally:
        main.app.dependency_overrides.pop(main.require_admin, None)
        main.app.dependency_overrides.pop(main.require_document_approver, None)


def test_document_review_validates_hash_and_review_fields(monkeypatch):
    main.app.dependency_overrides[main.require_admin] = lambda: True
    main.app.dependency_overrides[main.require_document_approver] = lambda: True
    monkeypatch.setattr(main, "get_lead", lambda lead_id: {"id": lead_id})
    try:
        client = TestClient(main.app)
        invalid_hash = client.post("/crm/leads/3/documents/not-a-hash/review", json={
            "decision": "accepted_for_next_step",
            "reviewer_reference": "reviewer@example.com",
            "reason": "Looks fine after visual inspection.",
        })
        assert invalid_hash.status_code == 400
        invalid_reason = client.post(f"/crm/leads/3/documents/{'c' * 64}/review", json={
            "decision": "accepted_for_next_step",
            "reviewer_reference": "reviewer@example.com",
            "reason": "ok",
        })
        assert invalid_reason.status_code == 422
    finally:
        main.app.dependency_overrides.pop(main.require_admin, None)
        main.app.dependency_overrides.pop(main.require_document_approver, None)
