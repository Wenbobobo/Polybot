from polybot.adapters.polymarket.relayer import RetryRelayer, OrderRequest


class FlakyInner:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary")
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]

    def cancel_client_orders(self, ids):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("temporary-cancel")
        from polybot.adapters.polymarket.relayer import CancelAck

        return [CancelAck(client_order_id=ids[0], canceled=True)]


def test_retry_relayer_retries_and_succeeds():
    rr = RetryRelayer(FlakyInner(), max_retries=1, retry_sleep_ms=0)
    req = OrderRequest(market_id="m", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    acks = rr.place_orders([req])
    assert acks and acks[0].accepted is True
    # cancel path retry
    acks2 = rr.cancel_client_orders(["cid"])
    assert acks2 and acks2[0].canceled is True

