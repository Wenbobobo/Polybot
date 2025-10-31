from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import get_counter_labelled


def test_quoter_skips_when_same_levels():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(size=1.0, min_requote_interval_ms=0, min_side_replace_interval_ms=0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    # First quote
    quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    # No movement, same quote should be skipped
    quoter.step(ob.apply_delta({"seq": 3}), now_ts_ms=1010, last_update_ts_ms=1005)
    assert get_counter_labelled("quotes_skipped_same", {"market": "m1"}) >= 1


def test_quoter_replaces_only_changed_side():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(size=1.0, min_requote_interval_ms=0, min_side_replace_interval_ms=0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    # Move only bid by > tick
    ob.apply_delta({"seq": 3, "bids": [[0.41, 1.0]]})
    quoter.step(ob.apply_delta({"seq": 4}), now_ts_ms=1100, last_update_ts_ms=1050)
    # Expect at least one cancel (bid) and placed intents at least one
    canceled = con.execute("SELECT COUNT(*) FROM orders WHERE status='canceled'").fetchone()[0]
    assert canceled >= 1
