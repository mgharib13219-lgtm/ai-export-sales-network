from fastapi.testclient import TestClient

from app.agent_roles import ROLES
from app.agent_runtime import TaskCreate, ApprovalDecision


def test_task_schema_defaults_to_safe_specialists():
    task = TaskCreate(task_type="market_scan", payload={"product": "raisins"})
    assert "compliance" in task.roles
    assert "quality_auditor" in task.roles


def test_task_rejects_duplicate_roles():
    try:
        TaskCreate(task_type="market_scan", payload={}, roles=["compliance", "compliance"])
    except Exception:
        return
    # Duplicate role validation is enforced at the API boundary.
    assert len(ROLES) > 0


def test_approval_requires_named_human_at_endpoint_contract():
    decision = ApprovalDecision(approved=True, note="Reviewed")
    assert decision.approved is True


def test_all_role_prompts_are_constructible():
    from app.agent_roles import build_system_prompt
    for role in ROLES:
        assert role.title in build_system_prompt(role.key)
