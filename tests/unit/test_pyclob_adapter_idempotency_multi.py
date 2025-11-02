from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer
from polybot.adapters.polymarket.relayer import OrderRequest


class StubClient:
    def __init__(self):
        self.sent = None

    def place_orders(self, payload):  # type: ignore[no-untyped-def]
        self.sent = payload
        # Ack both
        return [
            {"orderId": f"o{i}", "status": "accepted", "clientOrderId": p.get("clientOrderId")}
            for i, p in enumerate(payload)
        ]


def test_pyclob_adapter_idempotency_key_stable_multi_intents():
    stub = StubClient()
    rel = PyClobRelayer(stub)
    reqs = [
        OrderRequest(market_id="m", outcome_id="o1", side="buy", price=0.4, size=1.0, client_order_id="c1"),
        OrderRequest(market_id="m", outcome_id="o2", side="sell", price=0.6, size=2.0, client_order_id="c2"),
    ]
    rel.place_orders(reqs, idempotency_prefix="plan-k")
    keys = [o.get("idempotencyKey") for o in stub.sent]
    assert keys[0] == "plan-k:c1" and keys[1] == "plan-k:c2"
    # Repeat and ensure identical
    rel.place_orders(reqs, idempotency_prefix="plan-k")
    keys2 = [o.get("idempotencyKey") for o in stub.sent]
    assert keys == keys2

