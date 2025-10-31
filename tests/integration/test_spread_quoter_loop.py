from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter


def test_spread_quoter_quotes_on_move_and_skips_when_stable():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(tick_size=0.01, size=1.0, edge=0.02)
    quoter = SpreadQuoter(market_id="m1", outcome_yes_id="yes", params=params, engine=engine)

    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    # First step -> should quote
    res1 = quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    assert res1 is not None
    # No further move -> skip
    res2 = quoter.step(ob.apply_delta({"seq": 3}), now_ts_ms=1100, last_update_ts_ms=1000)
    assert res2 is None
    # Move best bid by a tick -> refresh
    ob.apply_delta({"seq": 4, "bids": [[0.41, 10.0]]})
    res3 = quoter.step(ob.apply_delta({"seq": 5}), now_ts_ms=1200, last_update_ts_ms=1100)
    assert res3 is not None

