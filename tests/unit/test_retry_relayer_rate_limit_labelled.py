from polybot.adapters.polymarket.relayer import RetryRelayer, OrderRequest
from polybot.observability.metrics import get_counter_labelled, reset as metrics_reset


class RateLimitError(Exception):
    pass


class FlakyInner:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            e = RateLimitError("Rate limit exceeded")
            setattr(e, "code", 429)
            raise e
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_retry_relayer_increments_labelled_events_per_market():
    metrics_reset()
    inner = FlakyInner()
    rr = RetryRelayer(inner, max_retries=1, retry_sleep_ms=0)
    reqs = [
        OrderRequest(market_id="m1", outcome_id="o", side="buy", price=0.4, size=1.0),
        OrderRequest(market_id="m2", outcome_id="o", side="sell", price=0.6, size=1.0),
    ]
    rr.place_orders(reqs, idempotency_prefix="p")
    assert get_counter_labelled("relayer_rate_limited_events", {"market": "m1"}) == 1
    assert get_counter_labelled("relayer_rate_limited_events", {"market": "m2"}) == 1

