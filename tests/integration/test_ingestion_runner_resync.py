import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.snapshot import FakeSnapshotProvider
from polybot.ingestion.runner import run_orderbook_stream


async def _aiter_messages(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_runner_resyncs_on_first_delta_and_gap():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")

    # First delta arrives without snapshot (seq 11), then a gap to 13
    messages = [
        {"type": "delta", "seq": 11, "bids": [[0.40, 10.0]]},
        {"type": "delta", "seq": 13, "asks": [[0.47, -5.0]]},
    ]
    # Snapshot provider returns seq 10
    provider = FakeSnapshotProvider({"type": "snapshot", "seq": 10, "bids": [[0.39, 100.0]], "asks": [[0.48, 100.0]]})

    await run_orderbook_stream("m1", _aiter_messages(messages), ing, provider)

    # Verify snapshot and 2 deltas applied/persisted
    cur = con.execute("SELECT COUNT(*) FROM orderbook_snapshots WHERE market_id='m1'")
    assert cur.fetchone()[0] >= 1
    cur = con.execute("SELECT COUNT(*) FROM orderbook_events WHERE market_id='m1'")
    assert cur.fetchone()[0] == 2

