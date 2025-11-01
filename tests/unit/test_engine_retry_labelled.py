from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.observability.metrics import get_counter_labelled


class FlakyRelayer:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("oops")
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=1.0, status="accepted")]


def test_engine_retry_increments_labelled_counter():
    before = get_counter_labelled("engine_retries", {"market": "m1"})
    engine = ExecutionEngine(FlakyRelayer(), audit_db=None, max_retries=1, retry_sleep_ms=0)
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)], expected_profit=0, rationale="r")
    engine.execute_plan(plan)
    after = get_counter_labelled("engine_retries", {"market": "m1"})
    assert after == before + 1

