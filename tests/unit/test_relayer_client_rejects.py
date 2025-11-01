from polybot.adapters.polymarket.relayer import RelayerClient, OrderRequest


class StubClient:
    def place_orders(self, orders):
        return [
            {
                "order_id": "o1",
                "status": "rejected",
                "filled_size": 0.0,
                "remaining_size": orders[0].get("size", 0.0),
                "client_order_id": orders[0].get("client_order_id"),
            }
        ]

    def cancel_orders(self, ids):
        return []


def test_relayer_client_maps_rejected_as_not_accepted():
    client = RelayerClient(StubClient())
    req = OrderRequest(market_id="m", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    acks = client.place_orders([req])
    assert acks and acks[0].accepted is False and acks[0].status == "rejected"
