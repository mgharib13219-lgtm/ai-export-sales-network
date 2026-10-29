from types import SimpleNamespace

import app.db as db


def test_agent_profiles_persist_product_and_enabled_state(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "settings", SimpleNamespace(
        database_url="", environment="development"
    ))
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "agent-test.sqlite")
    db.init_db()

    product = {"name": "Olive oil", "target_countries": ["Germany", "France"]}
    profile_id = db.save_agent_profile("EU olive oil", product, 720, enabled=True)

    profile = db.get_agent_profile(profile_id)
    assert profile["name"] == "EU olive oil"
    assert profile["product"] == product
    assert profile["enabled"] in (True, 1)
    assert profile["interval_minutes"] == 720

    db.save_agent_profile("Paused olive oil", product, 1440,
                          profile_id=profile_id, enabled=False)
    updated = db.get_agent_profile(profile_id)
    assert updated["enabled"] in (False, 0)
    assert db.list_agent_profiles(enabled_only=True) == []


def test_agent_run_history_does_not_expose_raw_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "settings", SimpleNamespace(
        database_url="", environment="development"
    ))
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "agent-runs.sqlite")
    db.init_db()
    profile_id = db.save_agent_profile("Test product", {"name": "Test product"})
    run_id = db.record_agent_run(profile_id, "failed", error_code="pipeline_error")
    runs = db.list_agent_runs()
    assert runs[0]["id"] == run_id
    assert runs[0]["status"] == "failed"
    assert runs[0]["error_code"] == "pipeline_error"
