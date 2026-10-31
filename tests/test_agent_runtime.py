from app.agent_roles import ROLES, build_system_prompt
from app.agent_runtime import TaskCreate, ApprovalDecision


def test_task_roles_are_unique_and_bounded():
    valid = TaskCreate(task_type="buyer_research", payload={"product": "any"})
    assert len(valid.roles) <= 8
    assert len(valid.roles) == len(set(valid.roles))


def test_task_role_count_limit_is_enforced():
    try:
        TaskCreate(task_type="buyer_research", payload={}, roles=[
            "orchestrator", "market_intelligence", "buyer_discovery", "supplier_onboarding",
            "compliance", "trust_safety", "matching", "catalogue", "commercial_advisor"
        ])
    except Exception:
        return
    raise AssertionError("more than eight roles must be rejected")


def test_approval_decision_is_only_a_recorded_boolean():
    approved = ApprovalDecision(approved=True, note="Reviewed scope")
    rejected = ApprovalDecision(approved=False, note="Insufficient evidence")
    assert approved.approved is True
    assert rejected.approved is False


def test_all_role_prompts_are_constructible():
    for role in ROLES:
        assert role.title in build_system_prompt(role.key)
