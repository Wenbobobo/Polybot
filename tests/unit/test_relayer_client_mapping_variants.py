from polybot.adapters.polymarket.relayer import RelayerClient, OrderRequest


class StubVariant:
    def place_orders(self, orders):
        return [
            {
                "orderId": "o1",
                "status": "partial",
                "filledSize": 0.5,
                "remainingSize": 0.5,
                "clientOrderId": orders[0].get("client_order_id") or orders[0].get("clientOrderId"),
            }
        ]

    def cancel_orders(self, ids):
        return [{"clientOrderId": ids[0], "status": "canceled"}]


def test_relayer_client_maps_variant_keys_and_cancel_status():
    rc = RelayerClient(StubVariant())
    req = OrderRequest(market_id="m", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    acks = rc.place_orders([req])
    assert acks[0].order_id == "o1"
    assert acks[0].accepted is True and acks[0].status == "partial"
    c = rc.cancel_client_orders(["cid"])
    assert c[0].canceled is True and c[0].client_order_id == "cid"

