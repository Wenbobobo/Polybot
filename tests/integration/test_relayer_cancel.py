from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_engine_cancel_client_orders_updates_db():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    relayer = FakeRelayer(fill_ratio=0.0)
    engine = ExecutionEngine(relayer, audit_db=con)

    plan = ExecutionPlan(
        intents=[
            OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0, tif="GTC", client_order_id="c_bid"),
            OrderIntent(market_id="m1", outcome_id="o1", side="sell", price=0.6, size=1.0, tif="GTC", client_order_id="c_ask"),
        ],
        expected_profit=0.2,
        rationale="spread-quote",
    )
    engine.execute_plan(plan)

    # Cancel both client orders
    engine.cancel_client_orders(["c_bid", "c_ask"])

    rows = con.execute("SELECT status FROM orders WHERE client_oid IN ('c_bid','c_ask') ORDER BY client_oid").fetchall()
    assert rows and all(r[0] == 'canceled' for r in rows)

