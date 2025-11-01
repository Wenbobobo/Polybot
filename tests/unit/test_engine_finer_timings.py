from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.observability.metrics import get_counter_labelled


def test_engine_records_place_call_timing():
    eng = ExecutionEngine(FakeRelayer(fill_ratio=0.0))
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)],
        expected_profit=0.0,
        rationale="t",
    )
    base = get_counter_labelled("engine_place_call_ms_sum", {"market": "m1"})
    eng.execute_plan(plan)
    now = get_counter_labelled("engine_place_call_ms_sum", {"market": "m1"})
    assert now >= base

