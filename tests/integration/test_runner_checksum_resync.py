import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.snapshot import FakeSnapshotProvider
from polybot.ingestion.runner import run_orderbook_stream
from polybot.core.checksum import orderbook_checksum


async def _aiter_messages(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_checksum_mismatch_triggers_resync_snapshot():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    # initial snapshot
    snap = {"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}
    ing.process(snap, ts_ms=1000)
    # Build a delta and compute expected checksum
    ing.assembler.apply_delta({"seq": 11, "bids": [[0.41, 1.0]]})
    local = orderbook_checksum(ing.assembler._bids, ing.assembler._asks)
    # Now send a mismatched checksum in the stream to force resync
    messages = [
        {"type": "delta", "seq": 12, "asks": [[0.59, 1.0]], "checksum": "BAD"},
    ]
    provider = FakeSnapshotProvider({"type": "snapshot", "seq": 12, "bids": [[0.42, 1.0]], "asks": [[0.58, 1.0]]})
    await run_orderbook_stream("m1", _aiter_messages(messages), ing, provider, now_ms=lambda: 2000)
    # Should have two snapshots now (initial + resync)
    cnt = con.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
    assert cnt >= 2

