from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.strategy.spread import plan_spread_quotes, SpreadParams


def _build_ob():
    ob = OrderbookAssembler(market_id="m1")
    ob.apply_snapshot({
        "seq": 1,
        "bids": [[0.40, 100.0], [0.39, 50.0]],
        "asks": [[0.47, 80.0], [0.48, 40.0]],
    })
    return ob


def test_spread_quotes_basic_inside_spread():
    ob = _build_ob()
    plan = plan_spread_quotes(
        market_id="m1",
        outcome_buy_id="yes",
        outcome_sell_id="yes",
        ob=ob.apply_delta({"seq": 2}),
        now_ts_ms=1500,
        last_update_ts_ms=1200,
        params=SpreadParams(tick_size=0.01, size=10.0, edge=0.02, staleness_threshold_ms=2000),
    )
    assert plan is not None
    bid = [i for i in plan.intents if i.side == "buy"][0]
    ask = [i for i in plan.intents if i.side == "sell"][0]
    assert 0.41 <= bid.price <= 0.46
    assert 0.41 <= ask.price <= 0.46
    assert bid.price < ask.price
    # Ensure inside the current spread [0.40, 0.47]
    assert bid.price >= 0.40
    assert ask.price <= 0.47


def test_spread_quotes_stale_orderbook_returns_none():
    ob = _build_ob()
    plan = plan_spread_quotes(
        market_id="m1",
        outcome_buy_id="yes",
        outcome_sell_id="yes",
        ob=ob.apply_delta({"seq": 2}),
        now_ts_ms=5000,
        last_update_ts_ms=1000,
        params=SpreadParams(staleness_threshold_ms=2000),
    )
    assert plan is None


def test_spread_quotes_too_narrow_spread_returns_none():
    ob = OrderbookAssembler(market_id="m1")
    ob.apply_snapshot({
        "seq": 1,
        "bids": [[0.45, 100.0]],
        "asks": [[0.46, 80.0]],
    })
    plan = plan_spread_quotes(
        market_id="m1",
        outcome_buy_id="yes",
        outcome_sell_id="yes",
        ob=ob.apply_delta({"seq": 2}),
        now_ts_ms=1500,
        last_update_ts_ms=1400,
        params=SpreadParams(edge=0.02, tick_size=0.01),
    )
    assert plan is None

