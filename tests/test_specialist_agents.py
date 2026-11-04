from agents.catalogue_editor import CatalogueEditorAgent
from agents.compliance_gatekeeper import ComplianceGatekeeper
from agents.quality_auditor import QualityAuditorAgent
from agents.supplier_onboarding import SupplierOnboardingAgent


def test_compliance_gate_never_claims_live_screening_or_clearance():
    result = ComplianceGatekeeper().run({
        "name": "Olive oil", "origin": "Country A", "hs_code": "1509",
        "target_countries": ["Germany"],
    })
    assert result["status"] == "NEEDS_REVIEW"
    assert result["live_screening_performed"] is False
    assert result["legal_clearance"] is False
    assert result["human_approval_required"] is True


def test_compliance_gate_blocks_explicit_risk_flags():
    result = ComplianceGatekeeper().run({
        "name": "Product", "origin": "Country A", "hs_code": "1234",
        "target_countries": ["Country B"], "sanctions_hit": True,
    })
    assert result["status"] == "BLOCKED"
    assert "possible_restricted_party_or_sanctions_match" in result["risk_flags"]


def test_compliance_gate_identifies_missing_core_inputs():
    result = ComplianceGatekeeper().run({"name": "Product"})
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert set(result["missing_inputs"]) == {"origin", "hs_code", "target_countries"}


def test_supplier_onboarding_lists_missing_evidence_without_verifying_claims():
    result = SupplierOnboardingAgent().run(
        {"company_name": "Example Ltd", "country": "A", "evidence": {}},
        {"name": "Olive oil", "origin": "A", "capacity_per_month": 10, "moq": 1},
    )
    assert result["status"] == "NEEDS_REVIEW"
    assert result["identity_verified"] is False
    assert result["certificates_verified"] is False
    assert "business_registration" in result["evidence_gaps"]


def test_catalogue_editor_preserves_seller_claims_and_does_not_invent():
    result = CatalogueEditorAgent().run({
        "name": "Olive oil", "description": "Extra virgin olive oil",
        "origin": "Country A", "hs_code": "1509",
        "certificates": ["ISO 22000"],
    })
    assert result["status"] == "draft_only"
    assert result["normalized_facts"]["certificates_claimed"] == ["ISO 22000"]
    assert "not independently verified" in result["catalogue_draft"]
    assert result["unsupported_claims_added"] is False
    assert result["publication_requires_owner_approval"] is True


def test_quality_auditor_flags_identity_and_outreach_safety_violations():
    result = QualityAuditorAgent().run({
        "matches": [{"verification": {"identity_verified": True}}],
        "lead_ids": [1],
        "outreach": [{"status": "sent", "approval_required": False}],
        "compliance_review": {"status": "NEEDS_REVIEW"},
    })
    assert result["status"] == "REJECT"
    assert {item["code"] for item in result["issues"]} >= {
        "automated_identity_claim", "outreach_without_human_gate"
    }
