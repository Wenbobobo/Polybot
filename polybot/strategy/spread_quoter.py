from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Optional

from polybot.core.models import OrderBook
from polybot.strategy.spread import plan_spread_quotes, SpreadParams, should_refresh_quotes
from polybot.exec.engine import ExecutionEngine
from polybot.exec.risk import will_exceed_exposure
from polybot.observability.metrics import inc_labelled
from polybot.core.ratelimit import TokenBucket


@dataclass
class QuoterState:
    last_bid: Optional[float] = None
    last_ask: Optional[float] = None
    last_mid: Optional[float] = None
    last_seq: int = 0
    open_client_oids: list[str] = None  # type: ignore[assignment]
    inventory: float = 0.0
    last_quote_ts_ms: int = 0
    rate: TokenBucket | None = None
    last_quoted_bid: float | None = None
    last_quoted_ask: float | None = None
    last_quoted_buy_size: float | None = None
    last_quoted_sell_size: float | None = None
    last_replace_bid_ts_ms: int = 0
    last_replace_ask_ts_ms: int = 0
    cancel_rate: TokenBucket | None = None


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
        # Enforce global quote lifetime guard first (no side replacement before this time has passed)
        if self.state.last_quote_ts_ms and (now_ts_ms - self.state.last_quote_ts_ms) < max(0, self.params.min_quote_lifetime_ms):
            return None
        elapsed_ok = (
            (self.state.last_quote_ts_ms == 0)
            or ((now_ts_ms - self.state.last_quote_ts_ms) >= self.params.min_requote_interval_ms)
        )
        # Rate limit
        if self.state.rate is None:
            self.state.rate = TokenBucket(capacity=self.params.rate_capacity, refill_per_sec=self.params.rate_refill_per_sec, tokens=self.params.rate_capacity)
        if not self.state.rate.allow(1.0, now_ms=now_ts_ms):
            inc_labelled("quotes_rate_limited", {"market": self.market_id})
            return None
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

        # Optionally override tick_size using market metadata from DB (if available)
        effective_tick = self.params.tick_size
        if getattr(self.engine, "audit_db", None) is not None:
            try:
                row = self.engine.audit_db.execute(
                    "SELECT tick_size FROM outcomes WHERE outcome_id=? LIMIT 1",
                    (self.outcome_yes_id,),
                ).fetchone()
                if row and float(row[0]) > 0:
                    effective_tick = float(row[0])
            except Exception:
                pass
        eff_params = replace(self.params, tick_size=effective_tick)

        plan = plan_spread_quotes(
            market_id=self.market_id,
            outcome_buy_id=self.outcome_yes_id,
            outcome_sell_id=self.outcome_yes_id,
            ob=ob,
            now_ts_ms=now_ts_ms,
            last_update_ts_ms=last_update_ts_ms,
            params=eff_params,
            last_mid=self.state.last_mid,
        )
        if plan is None:
            return None
        # Assign client order ids per side and cancel/replace policy
        # Inventory-aware sizing adjustment
        base = self.params.size
        inv = self.state.inventory
        max_inv = max(1e-9, self.params.max_inventory)
        amp = min(0.5, abs(inv) / max_inv * self.params.rebalance_ratio)
        buy_size = base * (1.0 - amp if inv > 0 else 1.0 + amp)
        sell_size = base * (1.0 + amp if inv > 0 else 1.0 - amp)

        intended = {}
        for it in plan.intents:
            side_tag = "bid" if it.side == "buy" else "ask"
            it.client_order_id = f"q:{self.market_id}:{ob.seq}:{side_tag}"
            it.size = buy_size if it.side == "buy" else sell_size
            intended[side_tag] = (it.price, it.size)

        # Determine replacement need per side based on min_change_ticks threshold and size change
        replace_sides: list[str] = []
        tick = effective_tick
        min_change = self.params.min_change_ticks * tick
        if "bid" in intended:
            p, s = intended["bid"]
            if self.state.last_quoted_bid is None or abs(p - (self.state.last_quoted_bid or 0.0)) >= min_change or (self.state.last_quoted_buy_size is not None and abs(s - self.state.last_quoted_buy_size) > 0):
                replace_sides.append("bid")
        if "ask" in intended:
            p, s = intended["ask"]
            if self.state.last_quoted_ask is None or abs(p - (self.state.last_quoted_ask or 0.0)) >= min_change or (self.state.last_quoted_sell_size is not None and abs(s - self.state.last_quoted_sell_size) > 0):
                replace_sides.append("ask")

        # Enforce per-side minimum replace interval
        side_intervals_ok: list[str] = []
        for side in replace_sides:
            if side == "bid":
                if self.state.last_replace_bid_ts_ms == 0 or (now_ts_ms - self.state.last_replace_bid_ts_ms) >= self.params.min_side_replace_interval_ms:
                    side_intervals_ok.append("bid")
            else:
                if self.state.last_replace_ask_ts_ms == 0 or (now_ts_ms - self.state.last_replace_ask_ts_ms) >= self.params.min_side_replace_interval_ms:
                    side_intervals_ok.append("ask")
        replace_sides = side_intervals_ok

        if not replace_sides:
            inc_labelled("quotes_skipped_same", {"market": self.market_id})
            return None

        # Cancel only sides to be replaced
        if self.state.open_client_oids:
            # Init cancel rate bucket
            if self.state.cancel_rate is None:
                self.state.cancel_rate = TokenBucket(capacity=self.params.cancel_rate_capacity, refill_per_sec=self.params.cancel_rate_refill_per_sec, tokens=self.params.cancel_rate_capacity)
            # Decide which sides we are allowed to cancel now
            permitted_sides: list[str] = []
            for side in replace_sides:
                if self.state.cancel_rate.allow(1.0, now_ms=now_ts_ms):
                    permitted_sides.append(side)
                else:
                    inc_labelled("quotes_cancel_rate_limited", {"market": self.market_id})
            # remove non-permitted sides from replacement
            replace_sides = permitted_sides
            to_cancel = []
            for oid in self.state.open_client_oids:
                if oid.endswith(":bid") and "bid" in replace_sides:
                    to_cancel.append(oid)
                if oid.endswith(":ask") and "ask" in replace_sides:
                    to_cancel.append(oid)
            if to_cancel:
                self.engine.cancel_client_orders(to_cancel)
                inc_labelled("quotes_canceled", {"market": self.market_id}, len(to_cancel))

        # Enforce inventory cap by suppressing side that increases exposure further
        if self.state.inventory >= self.params.max_inventory:
            plan.intents = [i for i in plan.intents if i.side != "buy"]
            replace_sides = [s for s in replace_sides if s != "bid"]
        elif self.state.inventory <= -self.params.max_inventory:
            plan.intents = [i for i in plan.intents if i.side != "sell"]
            replace_sides = [s for s in replace_sides if s != "ask"]
        # Retain only intents for sides that require replacement and are permitted (after cancel throttle)
        if replace_sides:
            plan.intents = [i for i in plan.intents if ((i.side == "buy" and "bid" in replace_sides) or (i.side == "sell" and "ask" in replace_sides))]
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
        # Update last quoted levels for replaced sides
        if "bid" in replace_sides and "bid" in intended:
            self.state.last_quoted_bid, self.state.last_quoted_buy_size = intended["bid"]
            self.state.last_replace_bid_ts_ms = now_ts_ms
        if "ask" in replace_sides and "ask" in intended:
            self.state.last_quoted_ask, self.state.last_quoted_sell_size = intended["ask"]
            self.state.last_replace_ask_ts_ms = now_ts_ms
        for ack, intent in zip(res.acks, plan.intents):
            if intent.side == "buy":
                self.state.inventory += ack.filled_size
            else:
                self.state.inventory -= ack.filled_size
        return res
