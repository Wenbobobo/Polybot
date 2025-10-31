from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, detect_dutch_book, plan_dutch_book_with_safety


def test_detect_dutch_book_rejects_other_variants():
    q = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="a", best_ask=0.3, tick_size=0.01, min_size=1.0, name="Other candidates"),
            OutcomeQuote(outcome_id="b", best_ask=0.3, tick_size=0.01, min_size=1.0, name="B"),
            OutcomeQuote(outcome_id="c", best_ask=0.3, tick_size=0.01, min_size=1.0, name="C"),
        ],
    )
    ok, _ = detect_dutch_book(q, min_profit_usdc=0.02)
    assert ok is False
    q2 = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="a", best_ask=0.3, tick_size=0.01, min_size=1.0, name="其他"),
            OutcomeQuote(outcome_id="b", best_ask=0.3, tick_size=0.01, min_size=1.0, name="B"),
            OutcomeQuote(outcome_id="c", best_ask=0.3, tick_size=0.01, min_size=1.0, name="C"),
        ],
    )
    ok2, _ = detect_dutch_book(q2, min_profit_usdc=0.02)
    assert ok2 is False


def test_plan_with_fees_and_slippage_blocks_when_margin_exhausted():
    q = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="y", best_ask=0.48, tick_size=0.01, min_size=1.0, name="Yes"),
            OutcomeQuote(outcome_id="n", best_ask=0.49, tick_size=0.01, min_size=1.0, name="No"),
        ],
    )
    # margin = 0.03; with fee 50 bps on total ask (=0.005) and slippage 1 tick total (=0.02) => eff_margin 0.005
    p = plan_dutch_book_with_safety(q, min_profit_usdc=0.02, safety_margin_usdc=0.0, fee_bps=50, slippage_ticks=1)
    assert p is None
    # With lower fee/slippage costs, plan allowed
    p2 = plan_dutch_book_with_safety(q, min_profit_usdc=0.02, safety_margin_usdc=0.0, fee_bps=10, slippage_ticks=0)
    assert p2 is not None

