import asyncio

import pytest

from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.runner import run_orderbook_stream
from polybot.ingestion.snapshot import FakeSnapshotProvider
from polybot.observability.metrics import get_counter_labelled


async def _aiter_msgs(msgs):
    for m in msgs:
        await asyncio.sleep(0)
        yield m


@pytest.mark.asyncio
async def test_duplicate_delta_triggers_gap_resync():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    snap = {"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}
    ing.process(snap)
    delta = {"type": "delta", "seq": 11, "bids": [[0.41, 1.0]]}
    ing.process(delta)

    before_first = get_counter_labelled("ingestion_resync_first_delta", {"market": "m1"})
    # Send a duplicate seq=11; run_orderbook_stream should see cur_seq=11 and delta_seq!=12 -> resync
    msgs = [{"type": "delta", "seq": 11, "asks": [[0.59, 1.0]]}]
    provider = FakeSnapshotProvider(snap)
    await run_orderbook_stream("m1", _aiter_msgs(msgs), ing, provider)
    after_first = get_counter_labelled("ingestion_resync_first_delta", {"market": "m1"})
    assert after_first == before_first + 1
