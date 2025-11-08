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


class ShortAckStub:
    def place_orders(self, orders):
        return []  # fewer responses than requests

    def cancel_orders(self, ids):
        return []


def test_pyclob_adapter_pads_missing_responses():
    adapter = PyClobRelayer(ShortAckStub())
    reqs = [
        OrderRequest(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0, client_order_id="c1"),
        OrderRequest(market_id="m1", outcome_id="o2", side="buy", price=0.3, size=2.0, client_order_id="c2"),
    ]
    acks = adapter.place_orders(reqs)
    assert len(acks) == 2
    assert all(not ack.accepted for ack in acks)
    assert all(ack.error for ack in acks)


class ErrorAckStub:
    def place_orders(self, orders):
        return [
            {
                "orderId": "ord-error",
                "status": "failed",
                "success": False,
                "errorMsg": "builder rejected",
                "clientOrderId": orders[0].get("clientOrderId"),
            }
        ]

    def cancel_orders(self, ids):
        return []


def test_pyclob_adapter_marks_error_responses_as_rejected():
    adapter = PyClobRelayer(ErrorAckStub())
    req = OrderRequest(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0, client_order_id="cid-x")
    ack = adapter.place_orders([req])[0]
    assert not ack.accepted
    assert ack.error == "builder rejected"
    assert ack.client_order_id == "cid-x"
