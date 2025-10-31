from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, AsyncIterator, List, Optional
import sqlite3

from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, plan_dutch_book
from polybot.exec.engine import ExecutionEngine
from polybot.exec.risk import will_exceed_exposure
from polybot.observability.metrics import inc_labelled


@dataclass
class DutchSpec:
    market_id: str
    outcomes: List[str]  # list of outcome_ids


class DutchRunner:
    """Assemble per-outcome books and trigger Dutch-book detection + execution.

    Expected message format (internal):
      {"type": "snapshot|delta", "seq": int, "bids": [...], "asks": [...], "outcome_id": "..."}
    """

    def __init__(
        self,
        spec: DutchSpec,
        engine: ExecutionEngine,
        min_profit_usdc: float = 0.02,
        default_size: float = 1.0,
        meta_db: Optional[sqlite3.Connection] = None,
        safety_margin_usdc: float = 0.0,
        fee_bps: float = 0.0,
        slippage_ticks: int = 0,
        guard_rule_hash: bool = True,
        allow_other: bool = False,
    ):
        self.spec = spec
        self.engine = engine
        self.min_profit_usdc = float(min_profit_usdc)
        self.default_size = float(default_size)
        self.safety_margin_usdc = float(safety_margin_usdc)
        self.fee_bps = float(fee_bps)
        self.slippage_ticks = int(slippage_ticks)
        self.books: Dict[str, OrderbookAssembler] = {oid: OrderbookAssembler(spec.market_id) for oid in spec.outcomes}
        self.meta_db = meta_db
        self.guard_rule_hash = bool(guard_rule_hash)
        self.allow_other = bool(allow_other)
        self._rule_hash_known: Optional[str] = None
        if self.meta_db is not None and self.guard_rule_hash:
            try:
                row = self.meta_db.execute("SELECT rule_hash FROM markets WHERE market_id=?", (self.spec.market_id,)).fetchone()
                self._rule_hash_known = row[0] if row else None
            except Exception:
                self._rule_hash_known = None

    def _market_quotes(self) -> Optional[MarketQuotes]:
        outs: List[OutcomeQuote] = []
        names: Dict[str, str] = {}
        ticks: Dict[str, float] = {}
        mins: Dict[str, float] = {}
        if self.meta_db is not None:
            cur = self.meta_db.execute("SELECT outcome_id, name, tick_size, min_size FROM outcomes WHERE market_id=?", (self.spec.market_id,))
            for oid, name, tick, mn in cur.fetchall():
                names[str(oid)] = name
                ticks[str(oid)] = float(tick)
                mins[str(oid)] = float(mn)
        for oid, asm in self.books.items():
            ob = asm.apply_delta({"seq": asm._seq})  # materialize
            ba = ob.best_ask()
            if not ba:
                return None
            outs.append(OutcomeQuote(outcome_id=oid, best_ask=ba.price, tick_size=ticks.get(oid, 0.01), min_size=mins.get(oid, 1.0), name=names.get(oid)))
        return MarketQuotes(market_id=self.spec.market_id, outcomes=outs)

    async def run(self, messages: AsyncIterator[Dict[str, Any]], now_ms) -> None:
        async for m in messages:
            oid = m.get("outcome_id")
            if not oid or oid not in self.books:
                continue
            typ = m.get("type")
            if typ == "snapshot":
                self.books[oid].apply_snapshot(m)
            elif typ == "delta":
                self.books[oid].apply_delta(m)
            else:
                continue

            quotes = self._market_quotes()
            if quotes is None:
                continue
            from polybot.strategy.dutch_book import plan_dutch_book_with_safety
            # rule_hash guard (detect change mid-run)
            if self.meta_db is not None and self.guard_rule_hash:
                row = self.meta_db.execute("SELECT rule_hash FROM markets WHERE market_id=?", (self.spec.market_id,)).fetchone()
                cur_hash = row[0] if row else None
                if self._rule_hash_known is None:
                    self._rule_hash_known = cur_hash
                elif cur_hash != self._rule_hash_known:
                    inc_labelled("dutch_rulehash_changed", {"market": self.spec.market_id}, 1)
                    continue

            from polybot.strategy.dutch_book import plan_dutch_book_with_safety
            plan = plan_dutch_book_with_safety(
                quotes,
                min_profit_usdc=self.min_profit_usdc,
                safety_margin_usdc=self.safety_margin_usdc,
                fee_bps=self.fee_bps,
                slippage_ticks=self.slippage_ticks,
                allow_other=self.allow_other,
                default_size=self.default_size,
            )
            if plan is None:
                continue
            # Deterministic plan_id for idempotency based on current outcome seqs
            seqsig = "+".join([f"{oid}:{asm._seq}" for oid, asm in sorted(self.books.items())])
            plan.plan_id = f"dutch:{self.spec.market_id}:{seqsig}"
            if getattr(self.engine, "audit_db", None) is not None:
                blocked, _ = will_exceed_exposure(self.engine.audit_db, plan, cap_per_outcome=self.default_size * 10)
                if blocked:
                    continue
            res = self.engine.execute_plan(plan)
            inc_labelled("dutch_orders_placed", {"market": self.spec.market_id}, len(res.acks))
