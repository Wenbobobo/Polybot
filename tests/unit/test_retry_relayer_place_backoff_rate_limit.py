from polybot.adapters.polymarket.relayer import RetryRelayer, OrderRequest
from polybot.observability.metrics import get_counter, reset as metrics_reset


class RateLimitError(Exception):
    def __init__(self, msg: str, code: int | None = None):
        super().__init__(msg)
        self.code = code


class FlakyPlaceInner:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise RateLimitError("rate limit exceeded", code=429)
        # Success path
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted", client_order_id=reqs[0].client_order_id)]


def test_retry_relayer_place_retries_on_rate_limit_and_counts():
    metrics_reset()
    inner = FlakyPlaceInner()
    seen = []

    def sleeper(ms: int):
        seen.append(ms)

    rr = RetryRelayer(inner, max_retries=1, retry_sleep_ms=123, sleeper=sleeper)
    req = OrderRequest(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0)
    out = rr.place_orders([req], idempotency_prefix="plan-x")
    assert len(out) == 1 and inner.calls == 2
    # One retry and one rate-limit event counted
    assert get_counter("relayer_retries_total") >= 1
    assert get_counter("relayer_rate_limited_total") >= 1
    assert seen == [123]


class IdempotencyCaptureInner:
    def __init__(self):
        self.last_prefix = None

    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        self.last_prefix = idempotency_prefix
        return [{"order_id": "o", "status": "accepted"}]


def test_retry_relayer_forwards_idempotency_prefix():
    inner = IdempotencyCaptureInner()
    rr = RetryRelayer(inner, max_retries=0)
    req = OrderRequest(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0)
    rr.place_orders([req], idempotency_prefix="plan-abc")
    assert inner.last_prefix == "plan-abc"
