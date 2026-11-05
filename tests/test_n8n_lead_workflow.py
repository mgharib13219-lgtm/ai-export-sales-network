import json
from pathlib import Path


def test_n8n_lead_workflow_is_inactive_and_has_separate_channel_gates():
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / "n8n"
        / "workflows"
        / "lead-intake-review.json"
    )
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

    assert workflow["active"] is False
    nodes = {node["name"]: node for node in workflow["nodes"]}

    validation = nodes["Validate lead evidence and contact basis"]["parameters"]["jsCode"]
    gmail_gate = nodes["Allow Gmail draft when contact email exists"]["parameters"]["jsCode"]
    telegram_gate = nodes["Require opt-in and operator approval for Telegram"]["parameters"]["jsCode"]

    # Catch literal backslash-n sequences that make the Code node source invalid.
    assert "\\n" not in validation
    assert "\\n" not in gmail_gate
    assert "\\n" not in telegram_gate
    assert "\n" in validation

    # Draft creation is not blocked by outreach approval; it does not send email.
    assert "contact_email" in gmail_gate
    assert "outreach_approved" not in gmail_gate
    assert "opt_in" not in gmail_gate

    # Telegram is the only branch with the explicit opt-in and operator gate.
    assert "lead.opt_in === true" in telegram_gate
    assert "lead.outreach_approved === true" in telegram_gate
    assert "telegram_chat_id" in telegram_gate

    connections = workflow["connections"]
    assert connections["Allow Gmail draft when contact email exists"]["main"][0][0]["node"] == (
        "Create Gmail draft for human review"
    )
    assert connections["Require opt-in and operator approval for Telegram"]["main"][0][0]["node"] == (
        "Send approved Telegram message"
    )
