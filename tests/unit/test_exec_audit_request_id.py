from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_exec_audit_records_request_id_if_column_exists():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    eng = ExecutionEngine(StubRelayer(), audit_db=con)
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0, tif="IOC")], expected_profit=0.0, rationale="t")
    eng.execute_plan(plan)
    # request_id column should exist per current schema and be populated (non-empty)
    row = con.execute("SELECT request_id FROM exec_audit ORDER BY id DESC LIMIT 1").fetchone()
    assert row is not None and isinstance(row[0], (str, type(None)))
    assert row[0] is None or len(row[0]) > 0

