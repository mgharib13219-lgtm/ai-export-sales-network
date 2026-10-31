from app.marketplace import _hash_password, _login_attempt_keys, _verify_password


def test_password_hashes_are_salted_and_verified():
    first = _hash_password("correct horse battery staple")
    second = _hash_password("correct horse battery staple")
    assert first != second
    assert _verify_password("correct horse battery staple", first)
    assert not _verify_password("wrong password", first)


def test_login_limiter_persists_only_hashed_account_and_client_identifiers():
    account_key, client_key = _login_attempt_keys("buyer@example.com", "203.0.113.10")
    assert len(account_key) == 64 and len(client_key) == 64
    assert "buyer@example.com" not in account_key
    assert "203.0.113.10" not in client_key
    assert account_key != client_key
