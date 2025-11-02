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
async def test_checksum_burst_without_resyncs():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    snap = {"type": "snapshot", "seq": 1, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}
    asm = OrderbookAssembler("m1")
    asm.apply_snapshot(snap)
    events: list[Dict[str, Any]] = [snap]
    # generate many deltas with correct checksums
    for i in range(2, 52):
        d = {"type": "delta", "seq": i, "bids": [[0.4 + i * 0.0001, 0.1]]}
        asm.apply_delta(d)
        d["checksum"] = orderbook_checksum(asm._bids, asm._asks)
        events.append(d)

    before = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    await run_orderbook_stream("m1", _aiter(events), ing, snapshot_provider=type("SP", (), {"get_snapshot": lambda _self, _mid: snap})())
    after = get_counter_labelled("ingestion_resync_checksum", {"market": "m1"})
    assert after == before
    # final seq applied
    assert ing.assembler._seq == 51

