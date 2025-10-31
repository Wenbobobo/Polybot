import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.snapshot import SnapshotProvider
from polybot.ingestion.runner import run_orderbook_stream_with_reconnect


class CountingSnapshotProvider:
    def __init__(self, snap: Dict[str, Any]):
        self.snap = dict(snap)
        self.calls = 0

    def get_snapshot(self, market_id: str) -> Dict[str, Any]:
        self.calls += 1
        return dict(self.snap)


def _gen_messages(parts: list[list[Dict[str, Any]]]):
    async def _factory() -> AsyncIterator[Dict[str, Any]]:
        # pop the next part
        if not parts:
            return
        chunk = parts.pop(0)
        for m in chunk:
            await asyncio.sleep(0)
            yield m
        # simulate connection drop
        raise RuntimeError("stream error")

    return _factory


@pytest.mark.asyncio
async def test_reconnects_and_throttles_snapshots():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    provider = CountingSnapshotProvider({"type": "snapshot", "seq": 0, "bids": [], "asks": []})

    parts = [
        [{"type": "delta", "seq": 1, "bids": [[0.4, 1.0]], "checksum": "x"}],
        [{"type": "delta", "seq": 2, "asks": [[0.6, 1.0]], "checksum": "y"}],
    ]

    now = 1000

    def now_ms():
        nonlocal now
        now += 10
        return now

    def sleep_ms(_):
        pass

    await run_orderbook_stream_with_reconnect(
        "m1",
        messages_factory=_gen_messages(parts),
        ingestor=ing,
        snapshot_provider=provider,  # type: SnapshotProvider
        now_ms=now_ms,
        max_retries=2,
        backoff_ms=1,
        snapshot_throttle_ms=1000,
        sleep_ms=sleep_ms,
    )
    # Only initial + at most one throttled resync despite two checksum mismatches
    assert provider.calls <= 2

