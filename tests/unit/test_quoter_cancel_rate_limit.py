from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_cancel_rate_limit_prevents_replacement():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    # cancel rate zero to force block
    params = SpreadParams(size=1.0, min_requote_interval_ms=0, cancel_rate_capacity=0.0, cancel_rate_refill_per_sec=0.0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    # move both sides but cancels are throttled so no cancel and no new intents
    ob.apply_delta({"seq": 3, "bids": [[0.41, 1.0]], "asks": [[0.46, 1.0]]})
    quoter.step(ob.apply_delta({"seq": 4}), now_ts_ms=1000, last_update_ts_ms=1000)
    canceled = con.execute("SELECT COUNT(*) FROM orders WHERE status='canceled'").fetchone()[0]
    assert canceled == 0
    # orders remain 2 (first placement) or more if other logic changed; ensure not more than initial by replacement
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt == 2

