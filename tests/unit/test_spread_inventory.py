from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def _build_env():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    ob = OrderbookAssembler("m1")
    ob.apply_snapshot({"seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]})
    return con, engine, ob


def test_inventory_positive_increases_sell_size_and_reduces_buy_size():
    con, engine, ob = _build_env()
    params = SpreadParams(size=10.0, max_inventory=100.0, rebalance_ratio=0.5)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    quoter.state.inventory = 50.0
    res = quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    assert res is not None
    # Extract intended sizes from audit intents
    row = con.execute("SELECT intents_json FROM exec_audit ORDER BY id DESC LIMIT 1").fetchone()
    assert row is not None
    import json

    intents = json.loads(row[0])
    sizes = {i["side"]: i["size"] for i in intents}
    assert sizes["sell"] > 10.0
    assert sizes["buy"] < 10.0


def test_min_requote_interval_prevents_frequent_quotes():
    con, engine, ob = _build_env()
    params = SpreadParams(size=10.0, min_requote_interval_ms=500)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    res1 = quoter.step(ob.apply_delta({"seq": 2}), now_ts_ms=1000, last_update_ts_ms=900)
    assert res1 is not None
    # Next step within interval: skip
    res2 = quoter.step(ob.apply_delta({"seq": 3}), now_ts_ms=1200, last_update_ts_ms=1100)
    assert res2 is None
    # After interval: allow
    res3 = quoter.step(ob.apply_delta({"seq": 4}), now_ts_ms=1700, last_update_ts_ms=1600)
    assert res3 is not None

