from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from polybot.core.models import OrderBook
from polybot.strategy.spread import plan_spread_quotes, SpreadParams, should_refresh_quotes
from polybot.exec.engine import ExecutionEngine


@dataclass
class QuoterState:
    last_bid: Optional[float] = None
    last_ask: Optional[float] = None
    last_mid: Optional[float] = None
    last_seq: int = 0


class SpreadQuoter:
    def __init__(self, market_id: str, outcome_yes_id: str, params: SpreadParams, engine: ExecutionEngine):
        self.market_id = market_id
        self.outcome_yes_id = outcome_yes_id
        self.params = params
        self.engine = engine
        self.state = QuoterState()

    def step(self, ob: OrderBook, now_ts_ms: Optional[int] = None, last_update_ts_ms: Optional[int] = None):
        now_ts_ms = now_ts_ms or int(time.time() * 1000)
        last_update_ts_ms = last_update_ts_ms or now_ts_ms
        bb = ob.best_bid()
        ba = ob.best_ask()
        if not bb or not ba:
            return None
        mid = (bb.price + ba.price) / 2.0

        # Decide whether to (re)quote
        if self.state.last_bid is not None and self.state.last_ask is not None:
            if not should_refresh_quotes(self.state.last_bid, self.state.last_ask, bb.price, ba.price, self.params.tick_size, self.params.max_mid_jump):
                return None

        plan = plan_spread_quotes(
            market_id=self.market_id,
            outcome_buy_id=self.outcome_yes_id,
            outcome_sell_id=self.outcome_yes_id,
            ob=ob,
            now_ts_ms=now_ts_ms,
            last_update_ts_ms=last_update_ts_ms,
            params=self.params,
            last_mid=self.state.last_mid,
        )
        if plan is None:
            return None
        res = self.engine.execute_plan(plan)
        # Update state with current levels regardless of fill
        self.state.last_bid = bb.price
        self.state.last_ask = ba.price
        self.state.last_mid = mid
        self.state.last_seq = ob.seq
        return res

