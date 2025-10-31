from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from polybot.core.pricing import round_to_tick, is_valid_price, sum_prices
from polybot.exec.planning import ExecutionPlan, OrderIntent


@dataclass
class OutcomeQuote:
    outcome_id: str
    best_ask: float
    tick_size: float
    min_size: float
    name: str | None = None


@dataclass
class MarketQuotes:
    market_id: str
    outcomes: List[OutcomeQuote]


def detect_dutch_book(
    quotes: MarketQuotes,
    min_profit_usdc: float = 0.02,
    allow_other: bool = False,
) -> Tuple[bool, float]:
    """Return (eligible, margin) for multi-outcome dutch-book opportunity.

    - Requires all outcomes to have valid best_ask in [0,1].
    - If allow_other is False, any outcome named 'Other' (case-insensitive) makes it ineligible.
    - Sum of asks must be < 1 - min_profit_usdc.
    """
    prices: List[float] = []
    for o in quotes.outcomes:
        if (o.name or "").strip().lower() == "other" and not allow_other:
            return False, 0.0
        p = o.best_ask
        if not is_valid_price(p):
            return False, 0.0
        prices.append(p)
    total = sum_prices(prices)
    margin = 1.0 - total
    return (margin > min_profit_usdc), margin


def plan_dutch_book(
    quotes: MarketQuotes,
    min_profit_usdc: float = 0.02,
    allow_other: bool = False,
    default_size: float = 1.0,
) -> ExecutionPlan | None:
    eligible, margin = detect_dutch_book(quotes, min_profit_usdc, allow_other)
    if not eligible:
        return None
    intents: List[OrderIntent] = []
    for o in quotes.outcomes:
        price = round_to_tick(o.best_ask, o.tick_size)
        size = max(default_size, o.min_size)
        intents.append(
            OrderIntent(
                market_id=quotes.market_id,
                outcome_id=o.outcome_id,
                side="buy",
                price=price,
                size=size,
                tif="IOC",
            )
        )
    return ExecutionPlan(intents=intents, expected_profit=margin * default_size, rationale="dutch_book_sum_lt_one")

