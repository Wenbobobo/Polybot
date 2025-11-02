from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.observability.metrics import get_counter_labelled, reset as metrics_reset


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_engine_ack_latency_metrics_increment():
    metrics_reset()
    eng = ExecutionEngine(StubRelayer())
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="yes", side="buy", price=0.4, size=1.0, tif="IOC")], expected_profit=0.0, rationale="test")
    eng.execute_plan(plan)
    # We expect a count increment for ack metrics even if duration is near 0ms
    assert get_counter_labelled("engine_ack_count", {"market": "m1"}) == 1
    # Sum exists (could be 0 on very fast machines, but label presence should be fine)
    assert get_counter_labelled("engine_ack_ms_sum", {"market": "m1"}) >= 0
