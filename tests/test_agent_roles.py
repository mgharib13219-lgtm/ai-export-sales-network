import pytest

from app.agent_roles import GLOBAL_RULES, ROLES, build_system_prompt, role_catalogue


def test_agent_roles_are_unique_and_have_boundaries():
    keys = [role.key for role in ROLES]
    assert len(keys) >= 10
    assert len(keys) == len(set(keys))
    for role in ROLES:
        assert role.mission
        assert role.allowed_actions
        assert role.prohibited_actions


def test_role_prompt_contains_global_safety_and_role_scope():
    prompt = build_system_prompt("compliance")
    assert "Never advise" in GLOBAL_RULES
    assert "ROLE: Trade Compliance Gatekeeper" in prompt
    assert "human_approval_required" in prompt
    assert "BLOCKED" in prompt


def test_unknown_agent_role_fails_closed():
    with pytest.raises(KeyError):
        build_system_prompt("superuser")


def test_role_catalogue_is_serializable():
    catalogue = role_catalogue()
    assert any(item["key"] == "trust_safety" for item in catalogue)
