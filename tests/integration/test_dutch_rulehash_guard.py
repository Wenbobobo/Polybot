import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.strategy.dutch_runner import DutchRunner, DutchSpec
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import get_counter_labelled


async def _aiter(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_rulehash_change_blocks_execution():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    con.execute("INSERT INTO markets (market_id, title, status, rule_hash) VALUES (?,?,?,?)", ("m1", "T", "active", "H1"))
    for oid in ("o1", "o2", "o3"):
        con.execute("INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)", (oid, "m1", "X", 0.01, 1.0))
    con.commit()
    spec = DutchSpec(market_id="m1", outcomes=["o1", "o2", "o3"])
    engine = ExecutionEngine(FakeRelayer(fill_ratio=1.0), audit_db=con)
    runner = DutchRunner(spec, engine, min_profit_usdc=0.02, default_size=1.0, meta_db=con, safety_margin_usdc=0.0)
    # Simulate rule_hash change before messages are processed
    con.execute("UPDATE markets SET rule_hash=? WHERE market_id=?", ("H2", "m1"))
    con.commit()
    msgs = [
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o1"},
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o2"},
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o3"},
    ]
    before = get_counter_labelled("dutch_orders_placed", {"market": "m1"})
    await runner.run(_aiter(msgs), now_ms=lambda: 0)
    after = get_counter_labelled("dutch_orders_placed", {"market": "m1"})
    assert after == before
    assert get_counter_labelled("dutch_rulehash_changed", {"market": "m1"}) >= 1

