import importlib

def _reload_db(monkeypatch, tmp_path):
    monkeypatch.setenv('ENVIRONMENT', 'development')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "test.db"}')
    import app.settings as settings_mod
    import app.db as db_mod
    importlib.reload(settings_mod)
    importlib.reload(db_mod)
    db_mod.init_db()
    return settings_mod, db_mod

def test_idempotency_claim_and_completion(monkeypatch, tmp_path):
    settings_mod, db = _reload_db(monkeypatch, tmp_path)
    first = db.claim_idempotency('req-123')
    assert first['claimed'] is True
    second = db.claim_idempotency('req-123')
    assert second['claimed'] is False
    assert second['status'] == 'processing'
    payload = {'status': 'human_review_required', 'lead_ids': [1, 2]}
    db.complete_idempotency('req-123', payload)
    third = db.claim_idempotency('req-123')
    assert third['claimed'] is False
    assert third['status'] == 'completed'
    assert third['payload'] == payload

def test_audit_event_round_trip(monkeypatch, tmp_path):
    settings_mod, db = _reload_db(monkeypatch, tmp_path)
    db.add_audit_event('pipeline.completed', 'admin', 'req-1', 'product', 'test-product', {'ok': True})
    rows = db.list_audit_events()
    assert rows[0]['event_type'] == 'pipeline.completed'
    assert rows[0]['request_id'] == 'req-1'
