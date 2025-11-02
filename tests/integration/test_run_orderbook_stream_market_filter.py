import asyncio

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.runner import run_orderbook_stream


async def _aiter(msgs):
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_runner_ignores_other_market_messages():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    snap_other = {"type": "snapshot", "seq": 1, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]], "market": "m2"}
    snap_this = {"type": "snapshot", "seq": 2, "bids": [[0.41, 1.0]], "asks": [[0.59, 1.0]], "market": "m1"}
    await run_orderbook_stream("m1", _aiter([snap_other, snap_this]), ing, snapshot_provider=type("SP", (), {"get_snapshot": lambda _s, _m: snap_this})())
    # Only one snapshot from m1 should be persisted
    cnt = con.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
    assert cnt == 1

