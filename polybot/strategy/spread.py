from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from polybot.core.models import OrderBook
from polybot.core.pricing import round_to_tick, is_valid_price
from polybot.exec.planning import ExecutionPlan, OrderIntent


@dataclass
class SpreadParams:
    tick_size: float = 0.01
    size: float = 10.0
    edge: float = 0.02  # distance from mid
    staleness_threshold_ms: int = 2000


def plan_spread_quotes(
    market_id: str,
    outcome_buy_id: str,
    outcome_sell_id: str,
    ob: OrderBook,
    now_ts_ms: int,
    last_update_ts_ms: int,
    params: SpreadParams = SpreadParams(),
) -> Optional[ExecutionPlan]:
    # Staleness guard
    if now_ts_ms - last_update_ts_ms > params.staleness_threshold_ms:
        return None

    best_bid = ob.best_bid()
    best_ask = ob.best_ask()
    if not best_bid or not best_ask:
        return None

    # If spread is too narrow relative to desired edge, skip quoting
    raw_spread = best_ask.price - best_bid.price
    min_required = max(2 * params.edge, 2 * params.tick_size)
    if raw_spread < min_required:
        return None

    # Compute mid and target quotes
    mid = (best_bid.price + best_ask.price) / 2.0
    raw_bid = max(best_bid.price + params.tick_size, mid - params.edge)
    raw_ask = min(best_ask.price - params.tick_size, mid + params.edge)

    bid_q = round_to_tick(max(0.0, min(raw_bid, best_ask.price - params.tick_size)), params.tick_size)
    ask_q = round_to_tick(min(1.0, max(raw_ask, best_bid.price + params.tick_size)), params.tick_size)

    # Ensure valid, inside spread and not crossed
    if not (is_valid_price(bid_q) and is_valid_price(ask_q)):
        return None
    if not (bid_q < ask_q and bid_q >= best_bid.price and ask_q <= best_ask.price):
        return None
    if ask_q - bid_q < params.tick_size:  # too tight / crossed after rounding
        return None

    intents = [
        OrderIntent(market_id=market_id, outcome_id=outcome_buy_id, side="buy", price=bid_q, size=params.size, tif="GTC"),
        OrderIntent(market_id=market_id, outcome_id=outcome_sell_id, side="sell", price=ask_q, size=params.size, tif="GTC"),
    ]
    return ExecutionPlan(intents=intents, expected_profit=ask_q - bid_q, rationale="spread_capture")
