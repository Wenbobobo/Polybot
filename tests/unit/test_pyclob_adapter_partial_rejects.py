from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer
from polybot.adapters.polymarket.relayer import OrderRequest


class StubClient:
    def __init__(self, acks):
        self._acks = acks
        self.sent = None

    def place_orders(self, payload):  # type: ignore[no-untyped-def]
        self.sent = payload
        return self._acks


def test_pyclob_adapter_maps_partial_fill_and_rejects_without_accepted_flag():
    # Two acks: one partial (camelCase sizes), one rejected (status only)
    acks = [
        {"orderId": "o1", "status": "partial", "filledSize": 0.4, "remainingSize": 0.6, "clientOrderId": "c1"},
        {"orderId": "o2", "status": "rejected", "clientOrderId": "c2"},
    ]
    stub = StubClient(acks)
    rel = PyClobRelayer(stub)
    reqs = [
        OrderRequest(market_id="m", outcome_id="y", side="buy", price=0.4, size=1.0, client_order_id="c1"),
        OrderRequest(market_id="m", outcome_id="y", side="buy", price=0.5, size=1.0, client_order_id="c2"),
    ]
    out = rel.place_orders(reqs, idempotency_prefix="plan-x")
    assert out[0].accepted is True and out[0].status == "partial" and abs(out[0].filled_size - 0.4) < 1e-9
    assert out[1].accepted is False and out[1].status == "rejected"
    # idempotencyKey forwarded
    assert stub.sent[0]["idempotencyKey"].startswith("plan-x:")

