from polybot.adapters.polymarket.relayer import RetryRelayer, OrderRequest
from polybot.observability.metrics import get_counter, reset as metrics_reset


class FlakyTimeoutInner:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("request timeout")
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_retry_relayer_classifies_timeout_on_place():
    metrics_reset()
    inner = FlakyTimeoutInner()
    rr = RetryRelayer(inner, max_retries=1, retry_sleep_ms=0)
    req = OrderRequest(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0)
    out = rr.place_orders([req], idempotency_prefix="p")
    assert len(out) == 1
    assert get_counter("relayer_retries_total") >= 1
    assert get_counter("relayer_timeouts_total") >= 1


class FlakyTimeoutCancelInner:
    def __init__(self):
        self.calls = 0

    def cancel_client_orders(self, client_oids):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("timeout waiting for cancel")
        from polybot.adapters.polymarket.relayer import CancelAck

        return [CancelAck(client_order_id=client_oids[0], canceled=True)]


def test_retry_relayer_classifies_timeout_on_cancel():
    metrics_reset()
    inner = FlakyTimeoutCancelInner()
    rr = RetryRelayer(inner, max_retries=1, retry_sleep_ms=0)
    out = rr.cancel_client_orders(["c1"])
    assert len(out) == 1
    assert get_counter("relayer_retries_total") >= 1
    assert get_counter("relayer_timeouts_total") >= 1

