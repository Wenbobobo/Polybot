import asyncio
import time
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.strategy.quoter_runner import QuoterRunner
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


async def _aiter_messages(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_quoter_runner_places_and_cancels_quotes():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = SpreadParams(size=1.0, min_requote_interval_ms=0)
    quoter = SpreadQuoter("m1", "yes", params, engine)
    runner = QuoterRunner("m1", quoter)

    msgs = [
        {"type": "snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "delta", "seq": 2},
        {"type": "delta", "seq": 3, "bids": [[0.41, 10.0]]},
    ]
    base = int(time.time() * 1000)
    now_ms = lambda: base

    await runner.run(_aiter_messages(msgs), now_ms)

    # Expect orders placed and canceled due to second quote replacing the first
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt >= 2
    canceled = con.execute("SELECT COUNT(*) FROM orders WHERE status='canceled'").fetchone()[0]
    assert canceled >= 2

