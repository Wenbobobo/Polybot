from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import get_counter_labelled


def test_quoter_rate_limit_skips_when_exceeded():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(size=1.0, min_requote_interval_ms=0, rate_capacity=1.0, rate_refill_per_sec=0.0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    # First quote allowed
    res1 = quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    assert res1 is not None
    # Second immediate attempt is rate-limited (no refill)
    res2 = quoter.step(ob.apply_delta({"seq": 3}), now_ts_ms=1000, last_update_ts_ms=1000)
    assert res2 is None
    assert get_counter_labelled("quotes_rate_limited", {"market": "m1"}) >= 1

