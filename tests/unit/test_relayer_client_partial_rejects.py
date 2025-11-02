from polybot.adapters.polymarket.relayer import RelayerClient, OrderRequest


class StubInner:
    def __init__(self, acks):
        self._acks = acks
        self.sent = None

    def place_orders(self, payload):  # type: ignore[no-untyped-def]
        self.sent = payload
        return self._acks


def test_relayer_client_maps_partial_fill_and_rejects():
    acks = [
        {"order_id": "o1", "status": "partial", "filled_size": 0.4, "remaining_size": 0.6, "client_order_id": "c1"},
        {"order_id": "o2", "status": "rejected", "client_order_id": "c2"},
    ]
    rc = RelayerClient(StubInner(acks))
    reqs = [
        OrderRequest(market_id="m", outcome_id="y", side="buy", price=0.4, size=1.0, client_order_id="c1"),
        OrderRequest(market_id="m", outcome_id="y", side="buy", price=0.5, size=1.0, client_order_id="c2"),
    ]
    out = rc.place_orders(reqs, idempotency_prefix="plan-x")
    assert out[0].accepted is True and out[0].status == "partial"
    assert out[1].accepted is False and out[1].status == "rejected"

