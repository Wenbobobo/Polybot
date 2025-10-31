from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer
from polybot.adapters.polymarket.relayer import OrderRequest


class StubPyClob:
    def __init__(self):
        self.sent = None

    def place_orders(self, orders):
        self.sent = orders
        return [
            {
                "orderId": "o1",
                "status": "partial",
                "filledSize": 0.5,
                "remainingSize": 0.5,
                "clientOrderId": orders[0].get("clientOrderId"),
            }
        ]

    def cancel_orders(self, ids):
        return [{"clientOrderId": cid, "canceled": True} for cid in ids]


def test_pyclob_adapter_maps_fields_and_idempotency():
    stub = StubPyClob()
    adapter = PyClobRelayer(stub)
    req = OrderRequest(
        market_id="m1",
        outcome_id="o1",
        side="buy",
        price=0.4,
        size=1.0,
        tif="IOC",
        client_order_id="cid1",
    )
    acks = adapter.place_orders([req], idempotency_prefix="plan-1")
    assert stub.sent[0]["idempotencyKey"].startswith("plan-1:")
    assert acks[0].order_id == "o1" and acks[0].status == "partial"
    c = adapter.cancel_client_orders(["cid1"])  # returns raw dicts, used by RelayerClient internally
    assert c and c[0]["canceled"] is True

