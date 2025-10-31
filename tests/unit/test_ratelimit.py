from polybot.core.ratelimit import TokenBucket


def test_token_bucket_allows_within_capacity_and_refill():
    tb = TokenBucket(capacity=2.0, refill_per_sec=1.0, tokens=2.0, last_refill_ms=1000)
    # consume two
    assert tb.allow(1.0, now_ms=1000) is True
    assert tb.allow(1.0, now_ms=1000) is True
    # third denied until refill
    assert tb.allow(1.0, now_ms=1000) is False
    # after 1.5s, should refill 1.5 tokens up to cap
    assert tb.allow(1.0, now_ms=2500) is True

