from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.strategy.spread import plan_spread_quotes, SpreadParams
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def test_execute_spread_quotes_with_fake_relayer():
    # Build orderbook
    ob = OrderbookAssembler(market_id="m1")
    ob.apply_snapshot({
        "seq": 1,
        "bids": [[0.40, 100.0]],
        "asks": [[0.47, 80.0]],
    })
    book = ob.apply_delta({"seq": 2})

    # Plan quotes
    plan = plan_spread_quotes(
        market_id="m1",
        outcome_buy_id="yes",
        outcome_sell_id="yes",
        ob=book,
        now_ts_ms=1500,
        last_update_ts_ms=1400,
        params=SpreadParams(tick_size=0.01, size=5.0, edge=0.02),
    )
    assert plan is not None

    # Execute
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0))
    result = engine.execute_plan(plan)
    assert len(result.acks) == 2
    assert result.fully_filled is True

