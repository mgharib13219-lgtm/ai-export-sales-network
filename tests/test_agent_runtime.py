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


from app.agent_runtime import _contains_side_effect_instruction


def test_nested_side_effect_directives_are_rejected():
    assert _contains_side_effect_instruction({"brief": {"send_email": True}})
    assert _contains_side_effect_instruction([{"payment": {"makePayment": {"amount": 10}}}])


def test_ordinary_research_payload_is_not_rejected():
    assert not _contains_side_effect_instruction({
        "product": "any product", "destination": "Germany",
        "research": ["market size", "import statistics"]
    })

from app.agent_runtime import _validate_agent_output


def test_agent_output_requires_complete_schema_and_explicit_human_gate():
    valid = {"status": "NEEDS_REVIEW", "findings": [], "sources": [],
             "assumptions": [], "confidence": 50, "risks_and_holds": [],
             "human_approval_required": True}
    assert _validate_agent_output(valid)
    assert not _validate_agent_output({**valid, "human_approval_required": False})
    assert not _validate_agent_output({**valid, "confidence": 101})
    assert not _validate_agent_output({"status": "COMPLETE"})

from app.agent_runtime import _payload_exceeds_limits


def test_agent_payload_depth_and_size_are_bounded():
    assert not _payload_exceeds_limits({"product": "generic goods"})
    assert _payload_exceeds_limits({"text": "x" * 10001})
    nested = {}
    cursor = nested
    for _ in range(12):
        cursor["next"] = {}
        cursor = cursor["next"]
    assert _payload_exceeds_limits(nested)

def test_approval_payload_limits_share_task_input_guards():
    from app.agent_runtime import _payload_exceeds_limits
    assert not _payload_exceeds_limits({"action": "review_only"})
    assert _payload_exceeds_limits({"document": "x" * 10001})
