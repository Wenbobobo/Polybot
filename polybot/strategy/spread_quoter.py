from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from polybot.core.models import OrderBook
from polybot.strategy.spread import plan_spread_quotes, SpreadParams, should_refresh_quotes
from polybot.exec.engine import ExecutionEngine
from polybot.exec.risk import will_exceed_exposure
from polybot.observability.metrics import inc_labelled


@dataclass
class QuoterState:
    last_bid: Optional[float] = None
    last_ask: Optional[float] = None
    last_mid: Optional[float] = None
    last_seq: int = 0
    open_client_oids: list[str] = None  # type: ignore[assignment]
    inventory: float = 0.0
    last_quote_ts_ms: int = 0


class SpreadQuoter:
    def __init__(self, market_id: str, outcome_yes_id: str, params: SpreadParams, engine: ExecutionEngine):
        self.market_id = market_id
        self.outcome_yes_id = outcome_yes_id
        self.params = params
        self.engine = engine
        self.state = QuoterState(open_client_oids=[])

    def step(self, ob: OrderBook, now_ts_ms: Optional[int] = None, last_update_ts_ms: Optional[int] = None):
        now_ts_ms = now_ts_ms or int(time.time() * 1000)
        last_update_ts_ms = last_update_ts_ms or now_ts_ms
        bb = ob.best_bid()
        ba = ob.best_ask()
        if not bb or not ba:
            return None
        mid = (bb.price + ba.price) / 2.0

        # Decide whether to (re)quote
        elapsed_ok = (
            (self.state.last_quote_ts_ms == 0)
            or ((now_ts_ms - self.state.last_quote_ts_ms) >= self.params.min_requote_interval_ms)
        )
        if self.state.last_bid is not None and self.state.last_ask is not None:
            movement = should_refresh_quotes(
                self.state.last_bid,
                self.state.last_ask,
                bb.price,
                ba.price,
                self.params.tick_size,
                self.params.max_mid_jump,
            )
            if not movement and not elapsed_ok:
                inc_labelled("quotes_skipped", {"market": self.market_id})
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
        # Assign client order ids per side and cancel previous
        # Inventory-aware sizing adjustment
        base = self.params.size
        inv = self.state.inventory
        max_inv = max(1e-9, self.params.max_inventory)
        amp = min(0.5, abs(inv) / max_inv * self.params.rebalance_ratio)
        buy_size = base * (1.0 - amp if inv > 0 else 1.0 + amp)
        sell_size = base * (1.0 + amp if inv > 0 else 1.0 - amp)

        for it in plan.intents:
            side_tag = "bid" if it.side == "buy" else "ask"
            it.client_order_id = f"q:{self.market_id}:{ob.seq}:{side_tag}"
            it.size = buy_size if it.side == "buy" else sell_size
        if self.state.open_client_oids:
            self.engine.cancel_client_orders(self.state.open_client_oids)
            inc_labelled("quotes_canceled", {"market": self.market_id}, len(self.state.open_client_oids))

        # Enforce inventory cap by suppressing side that increases exposure further
        if self.state.inventory >= self.params.max_inventory:
            plan.intents = [i for i in plan.intents if i.side != "buy"]
        elif self.state.inventory <= -self.params.max_inventory:
            plan.intents = [i for i in plan.intents if i.side != "sell"]
        # Risk check: do not execute if exposure cap would be exceeded
        if not plan.intents:
            return None
        blocked, _ = (False, 0.0)
        if getattr(self.engine, "audit_db", None) is not None:
            blocked, _ = will_exceed_exposure(self.engine.audit_db, plan, cap_per_outcome=self.params.max_inventory)
        if blocked:
            return None

        res = self.engine.execute_plan(plan)
        inc_labelled("quotes_placed", {"market": self.market_id}, len(plan.intents))
        self.state.open_client_oids = [i.client_order_id for i in plan.intents if i.client_order_id]
        # Update state with current levels regardless of fill
        self.state.last_bid = bb.price
        self.state.last_ask = ba.price
        self.state.last_mid = mid
        self.state.last_seq = ob.seq
        self.state.last_quote_ts_ms = now_ts_ms
        for ack, intent in zip(res.acks, plan.intents):
            if intent.side == "buy":
                self.state.inventory += ack.filled_size
            else:
                self.state.inventory -= ack.filled_size
        return res
