from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from polybot.storage.db import connect_sqlite, enable_wal
from polybot.storage import schema as schema_mod
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.observability.recording import read_jsonl
from polybot.observability.logging import setup_logging
from polybot.ingestion.runner import run_orderbook_stream
from polybot.ingestion.snapshot import SnapshotProvider, FakeSnapshotProvider
from polybot.adapters.polymarket.ws import OrderbookWSClient


def init_db(db_url: str):
    con = connect_sqlite(db_url)
    enable_wal(con)
    schema_mod.create_all(con)
    return con


def cmd_replay(file: str, market_id: str, db_url: str = ":memory:") -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    for event in read_jsonl(file):
        ing.process(event)


def cmd_status(db_url: str = ":memory:") -> str:
    """Return a human-readable status summary string for markets in DB."""
    con = connect_sqlite(db_url)
    rows = con.execute(
        "SELECT market_id, last_seq, last_update_ts_ms, snapshots, deltas FROM market_status ORDER BY market_id"
    ).fetchall()
    if not rows:
        return "No market status available."
    lines = ["market_id last_seq last_update_ms snapshots deltas"]
    for r in rows:
        lines.append(f"{r[0]} {r[1]} {r[2]} {r[3]} {r[4]}")
    out = "\n".join(lines)
    print(out)
    return out


async def _aiter_from_ws(url: str, max_messages: Optional[int] = None):
    count = 0
    async with OrderbookWSClient(url) as client:
        async for m in client.messages():
            yield m.raw
            count += 1
            if max_messages is not None and count >= max_messages:
                break


async def cmd_ingest_ws_async(url: str, market_id: str, snapshot_json: Optional[str] = None, db_url: str = ":memory:", max_messages: Optional[int] = None) -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    provider: SnapshotProvider
    if snapshot_json:
        import json

        snap = json.loads(Path(snapshot_json).read_text(encoding="utf-8"))
        provider = FakeSnapshotProvider(snap)
    else:
        provider = FakeSnapshotProvider({"type": "snapshot", "seq": 0, "bids": [], "asks": []})

    await run_orderbook_stream(market_id, _aiter_from_ws(url, max_messages=max_messages), ing, provider)


def cmd_ingest_ws(url: str, market_id: str, snapshot_json: Optional[str] = None, db_url: str = ":memory:", max_messages: Optional[int] = None) -> None:
    asyncio.run(cmd_ingest_ws_async(url, market_id, snapshot_json=snapshot_json, db_url=db_url, max_messages=max_messages))
