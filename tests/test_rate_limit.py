from app.rate_limit import SlidingWindowLimiter

def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.allow('client') is True
    assert limiter.allow('client') is True
    assert limiter.allow('client') is False

def test_rate_limiter_separates_clients():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    assert limiter.allow('a') is True
    assert limiter.allow('a') is False
    assert limiter.allow('b') is True
