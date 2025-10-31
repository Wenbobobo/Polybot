from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import get_counter_labelled


def test_engine_increments_labelled_duration():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0), audit_db=con)
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)],
        expected_profit=0,
        rationale="test",
    )
    base_count = get_counter_labelled("engine_execute_plan_count", {"market": "m1"})
    engine.execute_plan(plan)
    assert get_counter_labelled("engine_execute_plan_count", {"market": "m1"}) == base_count + 1

