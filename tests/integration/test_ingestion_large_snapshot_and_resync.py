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
async def test_large_snapshot_then_checksum_resync():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    # Large snapshot
    bids = [[0.10 + i * 0.0001, 1.0] for i in range(2000)]
    asks = [[0.60 + i * 0.0001, 1.0] for i in range(2000)]
    snap = {"type": "snapshot", "seq": 1, "bids": bids, "asks": asks}
    # Mismatch checksum delta to force resync
    delta = {"type": "delta", "seq": 2, "bids": [[bids[-1][0] + 0.001, 1.0]], "checksum": "BAD"}
    await run_orderbook_stream("m1", _aiter([snap, delta]), ing, snapshot_provider=type("SP", (), {"get_snapshot": lambda _s, _m: snap})())
    # Should have at least two snapshots: initial + resync due to checksum mismatch
    cnt = con.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
    assert cnt >= 2

