from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import OrderAck


class FlakyRelayer:
    def __init__(self):
        self.calls = 0

    def place_orders(self, reqs, idempotency_prefix=None):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary")
        return [
            OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")
        ]


def test_engine_retries_on_exception():
    slept = {"ms": 0}

    def sleeper(ms):
        slept["ms"] += ms

    engine = ExecutionEngine(FlakyRelayer(), audit_db=None, max_retries=1, retry_sleep_ms=5, sleeper=sleeper)
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)], expected_profit=0, rationale="r")
    res = engine.execute_plan(plan)
    assert len(res.acks) == 1
    assert slept["ms"] >= 5

