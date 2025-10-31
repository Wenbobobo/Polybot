from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

from polybot.adapters.polymarket.ws import OrderbookWSClient
from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.adapters.polymarket.subscribe import build_subscribe_l2
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite, enable_wal
from polybot.storage import schema as schema_mod
from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.strategy.quoter_runner import QuoterRunner


@dataclass
class MarketSpec:
    market_id: str
    outcome_yes_id: str
    ws_url: str
    subscribe: bool = True
    max_messages: Optional[int] = None
    spread_params: Optional[SpreadParams] = None


async def _aiter_translated_ws(url: str, max_messages: Optional[int] = None, subscribe_message: Optional[dict] = None) -> AsyncIterator[Dict[str, Any]]:
    count = 0
    async with OrderbookWSClient(url, subscribe_message=subscribe_message) as client:
        async for m in client.messages():
            out = translate_polymarket_message(m.raw)
            if out is None:
                continue
            yield out
            count += 1
            if max_messages is not None and count >= max_messages:
                break


class ServiceRunner:
    def __init__(self, db_url: str, params: Optional[SpreadParams] = None):
        self.db_url = db_url
        self.params = params or SpreadParams()
        self.con = connect_sqlite(db_url)
        enable_wal(self.con)
        schema_mod.create_all(self.con)

    async def run_markets(self, markets: List[MarketSpec]) -> None:
        engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=self.con)
        tasks: List[asyncio.Task] = []
        for ms in markets:
            sp = ms.spread_params or self.params
            quoter = SpreadQuoter(ms.market_id, ms.outcome_yes_id, sp, engine)
            runner = QuoterRunner(ms.market_id, quoter)
            sub = build_subscribe_l2(ms.market_id) if ms.subscribe else None
            now_ms = lambda: int(time.time() * 1000)
            coro = runner.run(_aiter_translated_ws(ms.ws_url, max_messages=ms.max_messages, subscribe_message=sub), now_ms)
            tasks.append(asyncio.create_task(coro))
        if tasks:
            await asyncio.gather(*tasks)
