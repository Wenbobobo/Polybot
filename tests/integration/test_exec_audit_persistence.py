from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_execution_audit_written_to_db():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0), audit_db=con)
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)],
        expected_profit=0.1,
        rationale="unit-test",
    )
    res = engine.execute_plan(plan)
    assert res.fully_filled is True
    cnt = con.execute("SELECT COUNT(*) FROM exec_audit").fetchone()[0]
    assert cnt == 1

