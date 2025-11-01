from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer
from polybot.adapters.polymarket.relayer import OrderRequest


class StubReject:
    def place_orders(self, orders):
        return [{"orderId": "o1", "status": "rejected", "clientOrderId": orders[0].get("clientOrderId") }]

    def cancel_orders(self, ids):
        return []


def test_pyclob_adapter_maps_rejected_status_to_not_accepted():
    adapter = PyClobRelayer(StubReject())
    req = OrderRequest(market_id="m", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    acks = adapter.place_orders([req])
    assert acks and acks[0].accepted is False

