import asyncio
from typing import AsyncIterator, Dict, Any

import pytest

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.ingestion.runner import run_orderbook_stream
from polybot.adapters.polymarket.orderbook import OrderbookAssembler
from polybot.core.checksum import orderbook_checksum
from polybot.observability.metrics import get_counter_labelled


async def _aiter(msgs: list[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_checksum_match_avoids_resync():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    snap = {"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}
    # Compute expected checksum after applying delta
    asm = OrderbookAssembler("m1")
    asm.apply_snapshot(snap)
    delta = {"type": "delta", "seq": 11, "bids": [[0.41, 1.0]]}
    asm.apply_delta(delta)
    expected = orderbook_checksum(asm._bids, asm._asks)
    delta_with_checksum = dict(delta)
    delta_with_checksum["checksum"] = expected

    before = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    await run_orderbook_stream("m1", _aiter([snap, delta_with_checksum]), ing, snapshot_provider=type("SP", (), {"get_snapshot": lambda _self, _mid: snap})())
    after = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    assert after == before

