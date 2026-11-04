from agents.document_evidence import DocumentEvidenceAgent


def test_document_agent_reports_missing_documents_without_claiming_verification():
    result = DocumentEvidenceAgent().run({}, today="2026-11-04")
    assert result["status"] == "NEEDS_REVIEW"
    assert "business_registration" in result["missing_documents"]
    assert result["authenticity_verified"] is False
    assert result["contents_extracted"] is False


def test_document_agent_flags_expired_and_expiring_documents():
    evidence = {
        "business_registration": {"reference": "doc-1", "expires_at": "2026-10-01"},
        "representative_authority": {"reference": "doc-2", "expires_at": "2026-11-20"},
        "product_specification": "seller-upload-ref",
        "certificate_evidence": "seller-upload-ref",
        "facility_or_production_evidence": "seller-upload-ref",
    }
    result = DocumentEvidenceAgent().run(evidence, today="2026-11-04")
    assert result["expired_documents"][0]["document"] == "business_registration"
    assert result["expiring_soon"][0]["document"] == "representative_authority"
    assert result["issuer_verified"] is False


def test_document_agent_accepts_complete_metadata_only_for_human_review():
    evidence = {key: "reference" for key in DocumentEvidenceAgent.REQUIRED_DOCUMENTS}
    result = DocumentEvidenceAgent().run(evidence, today="2026-11-04")
    assert result["status"] == "READY_FOR_HUMAN_REVIEW"
    assert result["human_review_required"] is True
    assert result["legal_or_compliance_clearance"] is False
