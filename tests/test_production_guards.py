import importlib

def test_production_requires_postgres(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///./data/test.db')
    import app.settings as settings_mod
    import app.db as db_mod
    importlib.reload(settings_mod)
    importlib.reload(db_mod)
    try:
        try:
            db_mod._con()
        except RuntimeError as exc:
            assert 'PostgreSQL' in str(exc)
        else:
            raise AssertionError('production accepted sqlite database')
    finally:
        monkeypatch.delenv('ENVIRONMENT', raising=False)
        monkeypatch.delenv('DATABASE_URL', raising=False)
        importlib.reload(settings_mod)
        importlib.reload(db_mod)

def test_private_hosts_are_rejected():
    from app.providers import ContactExtractor
    c=ContactExtractor()
    assert not c._public_host('http://127.0.0.1/')
    assert not c._public_host('http://localhost/')
