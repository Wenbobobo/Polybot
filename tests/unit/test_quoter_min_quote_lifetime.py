from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.core.models import OrderBook
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def make_book(bid: float, ask: float, seq: int = 1):
    return OrderBook(market_id="m1", seq=seq, bids={bid: 1.0}, asks={ask: 1.0})


def test_min_quote_lifetime_blocks_rapid_requote():
    params = SpreadParams(tick_size=0.01, size=1.0, edge=0.05, min_requote_interval_ms=0, min_quote_lifetime_ms=500)
    eng = ExecutionEngine(FakeRelayer(fill_ratio=0.0))
    q = SpreadQuoter("m1", "yes", params, eng)
    # First placement
    ob1 = make_book(0.40, 0.60, seq=1)
    res1 = q.step(ob1, now_ts_ms=1000, last_update_ts_ms=1000)
    assert res1 is not None
    # Second attempt within lifetime should be blocked even if movement
    ob2 = make_book(0.41, 0.61, seq=2)
    res2 = q.step(ob2, now_ts_ms=1200, last_update_ts_ms=1200)
    assert res2 is None

