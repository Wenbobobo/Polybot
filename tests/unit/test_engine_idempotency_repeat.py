from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent


class RecordRelayer:
    def __init__(self):
        self.calls = []

    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        self.calls.append((idempotency_prefix, [r.client_order_id for r in reqs]))
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_engine_reuses_client_oids_and_idempotency_on_repeat_execute():
    rel = RecordRelayer()
    eng = ExecutionEngine(relayer=rel)
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)],
        expected_profit=0.0,
        rationale="r",
        plan_id="plan-dup",
    )
    eng.execute_plan(plan)
    # Execute same plan again; client_order_id should remain stable
    eng.execute_plan(plan)
    assert len(rel.calls) == 2
    assert rel.calls[0][0] == rel.calls[1][0] == "plan-dup"
    assert rel.calls[0][1] == rel.calls[1][1]

