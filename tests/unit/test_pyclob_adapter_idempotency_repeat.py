from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer
from polybot.adapters.polymarket.relayer import OrderRequest


class StubClient:
    def __init__(self):
        self.sent_batches = []

    def place_orders(self, payload):  # type: ignore[no-untyped-def]
        # capture a copy
        self.sent_batches.append([dict(x) for x in payload])
        # echo back minimal accepted acks
        return [{"orderId": f"o{i}", "status": "accepted", "clientOrderId": p.get("clientOrderId") or p.get("client_order_id") or ""} for i, p in enumerate(payload)]


def test_pyclob_adapter_idempotency_key_stable_on_repeat():
    stub = StubClient()
    rel = PyClobRelayer(stub)
    req = OrderRequest(market_id="m", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    rel.place_orders([req], idempotency_prefix="plan-z")
    rel.place_orders([req], idempotency_prefix="plan-z")
    assert len(stub.sent_batches) == 2
    k1 = stub.sent_batches[0][0].get("idempotencyKey")
    k2 = stub.sent_batches[1][0].get("idempotencyKey")
    assert k1 == k2 and k1.startswith("plan-z:")

