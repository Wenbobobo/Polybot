from polybot.adapters.polymarket.relayer import build_relayer, OrderRequest


class StubPyClob:
    def __init__(self):
        self.sent = None

    def place_orders(self, orders):
        # capture payload to validate mapping
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


def test_build_relayer_real_wraps_pyclob_and_maps_fields():
    stub = StubPyClob()
    rel = build_relayer("real", client=stub)
    req = OrderRequest(
        market_id="m1",
        outcome_id="o1",
        side="buy",
        price=0.4,
        size=1.0,
        tif="IOC",
        client_order_id="cid1",
    )
    acks = rel.place_orders([req], idempotency_prefix="plan-xyz")
    # verify payload mapping to py-clob style
    sent = stub.sent
    assert sent is not None
    assert sent[0]["market"] == "m1"
    assert sent[0]["outcome"] == "o1"
    assert sent[0]["timeInForce"] == "IOC"
    assert sent[0]["clientOrderId"] == "cid1"
    assert sent[0]["idempotencyKey"].startswith("plan-xyz:")
    # verify ack mapping
    assert acks and acks[0].order_id == "o1"
    assert acks[0].status == "partial"
    assert acks[0].client_order_id == "cid1"

