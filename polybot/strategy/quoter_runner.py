from __future__ import annotations

from typing import Dict, Any, AsyncIterator

from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.strategy.spread_quoter import SpreadQuoter


class QuoterRunner:
    def __init__(self, market_id: str, quoter: SpreadQuoter):
        self.market_id = market_id
        self.quoter = quoter
        self.assembler = OrderbookAssembler(market_id)
        self.last_update_ts_ms = 0

    async def run(self, messages: AsyncIterator[Dict[str, Any]], now_ms) -> None:
        async for msg in messages:
            typ = msg.get("type")
            if typ == "snapshot":
                ob = self.assembler.apply_snapshot(msg)
            elif typ == "delta":
                ob = self.assembler.apply_delta(msg)
            else:
                continue
            ts = now_ms()
            self.quoter.step(ob, now_ts_ms=ts, last_update_ts_ms=ts)

