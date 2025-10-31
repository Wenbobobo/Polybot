from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, detect_dutch_book, plan_dutch_book


def test_detect_dutch_book_simple_yes_no_sum_lt_one():
    quotes = MarketQuotes(
        market_id="m1",
        outcomes=[
            OutcomeQuote(outcome_id="y", best_ask=0.48, tick_size=0.01, min_size=1.0, name="Yes"),
            OutcomeQuote(outcome_id="n", best_ask=0.49, tick_size=0.01, min_size=1.0, name="No"),
        ],
    )
    eligible, margin = detect_dutch_book(quotes, min_profit_usdc=0.02)
    assert eligible is True
    assert margin > 0.02


def test_detect_dutch_book_reject_other_by_default():
    quotes = MarketQuotes(
        market_id="m2",
        outcomes=[
            OutcomeQuote(outcome_id="a", best_ask=0.3, tick_size=0.01, min_size=1.0, name="A"),
            OutcomeQuote(outcome_id="b", best_ask=0.3, tick_size=0.01, min_size=1.0, name="B"),
            OutcomeQuote(outcome_id="o", best_ask=0.3, tick_size=0.01, min_size=1.0, name="Other"),
        ],
    )
    eligible, _ = detect_dutch_book(quotes, min_profit_usdc=0.02)
    assert eligible is False


def test_plan_dutch_book_generates_intents():
    quotes = MarketQuotes(
        market_id="m3",
        outcomes=[
            OutcomeQuote(outcome_id="o1", best_ask=0.2, tick_size=0.01, min_size=1.0, name="X"),
            OutcomeQuote(outcome_id="o2", best_ask=0.2, tick_size=0.01, min_size=1.0, name="Y"),
            OutcomeQuote(outcome_id="o3", best_ask=0.2, tick_size=0.01, min_size=1.0, name="Z"),
            OutcomeQuote(outcome_id="o4", best_ask=0.2, tick_size=0.01, min_size=1.0, name="W"),
            OutcomeQuote(outcome_id="o5", best_ask=0.17, tick_size=0.01, min_size=1.0, name="Q"),
        ],
    )
    plan = plan_dutch_book(quotes, min_profit_usdc=0.02)
    assert plan is not None
    assert len(plan.intents) == 5
    for i in plan.intents:
        assert i.side == "buy"
        assert i.tif == "IOC"
