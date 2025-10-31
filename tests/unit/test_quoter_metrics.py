from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import get_counter_labelled


def test_quoter_metrics_increment():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(size=1.0, min_requote_interval_ms=0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    # First quote -> placed
    quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    assert get_counter_labelled("quotes_placed", {"market": "m1"}) >= 1
    # Second within no movement but allowed by interval 0: still quote; to test skipped, enforce interval and no move
    quoter.params.min_requote_interval_ms = 100
    quoter.step(ob.apply_delta({"seq": 3}), now_ts_ms=1010, last_update_ts_ms=1005)
    assert get_counter_labelled("quotes_skipped", {"market": "m1"}) >= 1

