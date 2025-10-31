from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, plan_dutch_book
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def test_execute_dutch_book_with_fake_relayer():
    quotes = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="o1", best_ask=0.32, tick_size=0.01, min_size=1.0, name="A"),
            OutcomeQuote(outcome_id="o2", best_ask=0.32, tick_size=0.01, min_size=1.0, name="B"),
            OutcomeQuote(outcome_id="o3", best_ask=0.32, tick_size=0.01, min_size=1.0, name="C"),
        ],
    )
    plan = plan_dutch_book(quotes, min_profit_usdc=0.02, default_size=1.0)
    assert plan is not None
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0))
    res = engine.execute_plan(plan)
    assert res.fully_filled is True
    assert len(res.acks) == 3
