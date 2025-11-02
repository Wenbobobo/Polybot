from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_exec_audit_persists_timings_columns_if_present():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    eng = ExecutionEngine(StubRelayer(), audit_db=con)
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0, tif="IOC")], expected_profit=0.0, rationale="t")
    eng.execute_plan(plan)
    row = con.execute("SELECT duration_ms, place_call_ms, ack_latency_ms FROM exec_audit ORDER BY id DESC LIMIT 1").fetchone()
    # Columns exist and are integers >= 0
    assert row is not None
    assert all(isinstance(v, (int, float)) for v in row)
    assert all((v is None) or (v >= 0) for v in row)

