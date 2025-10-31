from dataclasses import asdict

from polybot.adapters.polymarket.relayer import OrderRequest
from polybot.adapters.polymarket.relayer import RelayerClient


class StubPyClob:
    def __init__(self):
        self.placed = []
        self.canceled = []

    def place_orders(self, orders):
        self.placed.append(orders)
        # Echo back mock acks with partial fills and accept/reject
        acks = []
        for o in orders:
            if o.get("price", 0) < 0 or o.get("size", 0) <= 0:
                acks.append({
                    "order_id": f"e-{o.get('client_order_id','')}",
                    "accepted": False,
                    "filled_size": 0.0,
                    "remaining_size": 0.0,
                    "status": "rejected",
                    "client_order_id": o.get("client_order_id"),
                })
            else:
                filled = round(o.get("size", 0) * 0.5, 10)
                remaining = max(0.0, o.get("size", 0) - filled)
                acks.append({
                    "order_id": f"id-{o.get('client_order_id','')}",
                    "accepted": True,
                    "filled_size": filled,
                    "remaining_size": remaining,
                    "status": "partial" if remaining > 0 else "filled",
                    "client_order_id": o.get("client_order_id"),
                })
        return acks

    def cancel_orders(self, client_order_ids):
        self.canceled.append(client_order_ids)
        return [{"client_order_id": cid, "canceled": True} for cid in client_order_ids]


def test_relayer_client_places_and_maps_acks():
    client = RelayerClient(StubPyClob())
    reqs = [
        OrderRequest(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=2.0, client_order_id="c1"),
        OrderRequest(market_id="m1", outcome_id="o2", side="sell", price=-1.0, size=1.0, client_order_id="c2"),
    ]
    acks = client.place_orders(reqs)
    assert len(acks) == 2
    # First accepted and partial
    assert acks[0].accepted and acks[0].status in ("partial", "filled")
    assert acks[0].filled_size > 0 and acks[0].remaining_size >= 0
    # Second rejected
    assert not acks[1].accepted and acks[1].status == "rejected"


def test_relayer_client_passes_idempotency_and_cancel():
    stub = StubPyClob()
    client = RelayerClient(stub)
    req = OrderRequest(market_id="m1", outcome_id="o1", side="buy", price=0.5, size=1.0, client_order_id="X")
    client.place_orders([req], idempotency_prefix="plan-123")
    # Ensure idempotency key attached
    sent = stub.placed[-1][0]
    assert sent.get("idempotency_key", "").startswith("plan-123:")
    # Cancel
    cacks = client.cancel_client_orders(["X"]) 
    assert cacks and cacks[0].canceled

