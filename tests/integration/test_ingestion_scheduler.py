import asyncio
import time
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.snapshot import FakeSnapshotProvider
from polybot.ingestion.scheduler import run_ingestion_session


async def _aiter_messages(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0.01)
        yield m


@pytest.mark.asyncio
async def test_scheduler_takes_snapshots_and_prunes():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    provider = FakeSnapshotProvider({"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]})

    msgs = [
        {"type": "delta", "seq": 11, "bids": [[0.41, 1.0]]},
        {"type": "delta", "seq": 12, "asks": [[0.59, 1.0]]},
    ]

    base = int(time.time() * 1000)
    fake_now = lambda: base + 500  # scheduler time
    fake_now_msgs = lambda: base + 5  # message timestamps

    await run_ingestion_session(
        "m1",
        _aiter_messages(msgs),
        ing,
        provider,
        snapshot_interval_ms=50,
        prune_interval_ms=50,
        retention_ms=10,
        now_ms=fake_now,
        messages_now_ms=fake_now_msgs,
    )

    # We should have at least one snapshot (from scheduler); events pruned due to low retention
    snaps = con.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
    assert snaps >= 1
    events = con.execute("SELECT COUNT(*) FROM orderbook_events").fetchone()[0]
    assert events == 0
