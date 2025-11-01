import sqlite3

from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.core.models import OrderBook
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage import schema


def make_book(bid: float, ask: float, seq: int = 1):
    return OrderBook(market_id="m1", seq=seq, bids={bid: 1.0}, asks={ask: 1.0})


def test_quoter_uses_tick_from_db_for_replace_threshold():
    # Setup DB with outcomes tick_size=0.05 for outcome 'yes'
    con = sqlite3.connect(":memory:")
    schema.create_all(con)
    con.execute("INSERT INTO markets (market_id, title, status) VALUES (?,?,?)", ("m1", "t", "open"))
    con.execute(
        "INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)",
        ("yes", "m1", "Yes", 0.05, 1.0),
    )
    con.commit()
    params = SpreadParams(tick_size=0.01, size=1.0, edge=0.05, min_requote_interval_ms=0, min_change_ticks=1)
    eng = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    q = SpreadQuoter("m1", "yes", params, eng)
    # First placement
    res1 = q.step(make_book(0.40, 0.60, seq=1), now_ts_ms=1000, last_update_ts_ms=1000)
    assert res1 is not None
    # Move best bid by only 0.01 (< db tick 0.05). Should skip replacement.
    res2 = q.step(make_book(0.41, 0.61, seq=2), now_ts_ms=2000, last_update_ts_ms=2000)
    assert res2 is None

