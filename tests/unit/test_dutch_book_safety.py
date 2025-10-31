from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, plan_dutch_book_with_safety


def test_plan_dutch_book_respects_safety_margin():
    # 2 outcomes 0.49 + 0.49 = 0.98 => margin = 0.02
    quotes = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="y", best_ask=0.49, tick_size=0.01, min_size=1.0, name="Yes"),
            OutcomeQuote(outcome_id="n", best_ask=0.49, tick_size=0.01, min_size=1.0, name="No"),
        ],
    )
    # With safety 0.01, margin 0.02 > 0.02+0.01? false => None
    p1 = plan_dutch_book_with_safety(quotes, min_profit_usdc=0.02, safety_margin_usdc=0.01)
    assert p1 is None
    # With safety 0.0, plan allowed
    p2 = plan_dutch_book_with_safety(quotes, min_profit_usdc=0.02, safety_margin_usdc=0.0)
    assert p2 is not None

