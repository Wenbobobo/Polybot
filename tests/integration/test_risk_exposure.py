from polybot.exec.risk import compute_inventory, will_exceed_exposure
from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_will_exceed_exposure_blocks_plan_when_cap_reached():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0), audit_db=con)
    # Place a buy fill of size 5
    plan1 = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=5.0)], expected_profit=0, rationale="seed")
    engine.execute_plan(plan1)
    assert abs(compute_inventory(con, "m1", "o1") - 5.0) < 1e-9

    # New plan would push inventory to 11 > cap=10
    plan2 = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=6.0)], expected_profit=0, rationale="test")
    blocked, inv = will_exceed_exposure(con, plan2, cap_per_outcome=10.0)
    assert blocked is True and inv == 5.0

    # A sell of 3 will reduce exposure, allowed
    plan3 = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="sell", price=0.6, size=3.0)], expected_profit=0, rationale="test")
    blocked2, _ = will_exceed_exposure(con, plan3, cap_per_outcome=10.0)
    assert blocked2 is False

