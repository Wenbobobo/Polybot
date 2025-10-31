from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_orders_and_fills_persisted_on_execute():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    plan = ExecutionPlan(
        intents=[
            OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=2.0, tif="GTC", client_order_id="c1"),
            OrderIntent(market_id="m1", outcome_id="o1", side="sell", price=0.6, size=2.0, tif="GTC", client_order_id="c2"),
        ],
        expected_profit=0.2,
        rationale="spread-quote",
    )
    res = engine.execute_plan(plan)
    assert res.fully_filled is False
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt == 2
    # No fills because fill_ratio=0
    fcnt = con.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
    assert fcnt == 0

