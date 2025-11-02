import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.runner import run_orderbook_stream_with_reconnect
from polybot.observability.metrics import get_counter_labelled


def _factory_parts(parts: list[list[Dict[str, Any]]]):
    async def _factory() -> AsyncIterator[Dict[str, Any]]:
        if not parts:
            return
        chunk = parts.pop(0)
        for m in chunk:
            await asyncio.sleep(0)
            yield m
        # simulate drop
        raise RuntimeError("drop")

    return _factory


@pytest.mark.asyncio
async def test_checksum_mismatch_across_reconnect_increments_metric():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    snap = {"type": "snapshot", "seq": 1, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}
    d1 = {"type": "delta", "seq": 2, "bids": [[0.41, 1.0]], "checksum": "BAD"}
    d2 = {"type": "delta", "seq": 3, "asks": [[0.59, 1.0]], "checksum": "BAD"}
    parts = [[d1], [d2]]

    before = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    await run_orderbook_stream_with_reconnect(
        market_id="m1",
        messages_factory=_factory_parts(parts),
        ingestor=ing,
        snapshot_provider=type("SP", (), {"get_snapshot": lambda _s, _m: snap})(),
        now_ms=lambda: 0,
        max_retries=2,
        backoff_ms=1,
        snapshot_throttle_ms=1000,
        sleep_ms=lambda ms: None,
    )
    after = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    assert after > before

