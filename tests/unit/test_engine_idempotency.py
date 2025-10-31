from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import OrderAck


class IdempStubRelayer:
    def __init__(self):
        self.last_idemp = None
        self.last_reqs = None

    def place_orders(self, reqs, idempotency_prefix=None):
        self.last_idemp = idempotency_prefix
        self.last_reqs = reqs
        acks = []
        for i, r in enumerate(reqs):
            acks.append(
                OrderAck(
                    order_id=f"oid-{i}",
                    accepted=True,
                    filled_size=0.0,
                    remaining_size=r.size,
                    status="accepted",
                    client_order_id=r.client_order_id,
                )
            )
        return acks


def test_engine_generates_client_oids_and_passes_idempotency():
    rel = IdempStubRelayer()
    engine = ExecutionEngine(relayer=rel, audit_db=None)
    plan = ExecutionPlan(
        intents=[
            OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0),
            OrderIntent(market_id="m1", outcome_id="o2", side="sell", price=0.6, size=1.0),
        ],
        expected_profit=0.0,
        rationale="test",
        plan_id="plan-xyz",
    )
    res = engine.execute_plan(plan)
    assert rel.last_idemp == "plan-xyz"
    assert all(r.client_order_id for r in rel.last_reqs)
    # The plan intents should also be populated with client_order_id for persistence paths
    assert all(i.client_order_id for i in plan.intents)
    assert len(res.acks) == 2

