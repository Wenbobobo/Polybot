from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import build_relayer


class StubPyClob:
    def __init__(self):
        self.sent = None

    def place_orders(self, orders):
        self.sent = orders
        return [
            {
                "orderId": "o1",
                "status": "accepted",
                "filledSize": 0.0,
                "remainingSize": orders[0].get("size", 0.0),
                "clientOrderId": orders[0].get("clientOrderId"),
            }
        ]

    def cancel_orders(self, ids):
        return [{"clientOrderId": cid, "canceled": True} for cid in ids]


def test_engine_passes_idempotency_prefix_to_pyclob_adapter():
    stub = StubPyClob()
    rel = build_relayer("real", client=stub)
    eng = ExecutionEngine(rel)
    plan = ExecutionPlan(
        intents=[
            OrderIntent(
                market_id="m1",
                outcome_id="o1",
                side="buy",
                price=0.4,
                size=1.0,
                tif="IOC",
                client_order_id="cid1",
            )
        ],
        expected_profit=0.0,
        rationale="t",
    )
    eng.execute_plan(plan)
    # The adapter should have received an idempotencyKey derived from plan_id
    assert stub.sent is not None
    assert "idempotencyKey" in stub.sent[0]

