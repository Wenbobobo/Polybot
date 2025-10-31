from __future__ import annotations

import asyncio
import contextlib
import time
from typing import AsyncIterator, Dict, Any, Optional, Callable

from .orderbook import OrderbookIngestor
from .runner import run_orderbook_stream
from .snapshot import SnapshotProvider


async def _periodic_snapshot(ing: OrderbookIngestor, interval_ms: int, now_ms: Callable[[], int]) -> None:
    try:
        while True:
            await asyncio.sleep(interval_ms / 1000.0)
            ing.persist_snapshot_now(ts_ms=now_ms())
    except asyncio.CancelledError:
        return


async def _periodic_prune(ing: OrderbookIngestor, interval_ms: int, retention_ms: int, now_ms: Callable[[], int]) -> None:
    try:
        while True:
            await asyncio.sleep(interval_ms / 1000.0)
            threshold = now_ms() - retention_ms
            ing.prune_events_before(threshold)
    except asyncio.CancelledError:
        return


async def run_ingestion_session(
    market_id: str,
    messages: AsyncIterator[Dict[str, Any]],
    ingestor: OrderbookIngestor,
    snapshot_provider: SnapshotProvider,
    snapshot_interval_ms: int = 30000,
    prune_interval_ms: int = 60000,
    retention_ms: int = 5 * 60_000,
    now_ms: Optional[Callable[[], int]] = None,
    messages_now_ms: Optional[Callable[[], int]] = None,
) -> None:
    """Run an ingestion session with periodic snapshot and pruning tasks.

    Terminates when the message stream ends; background tasks are cancelled.
    """
    now_ms = now_ms or (lambda: int(time.time() * 1000))
    snap_task = asyncio.create_task(_periodic_snapshot(ingestor, snapshot_interval_ms, now_ms))
    prune_task = asyncio.create_task(_periodic_prune(ingestor, prune_interval_ms, retention_ms, now_ms))
    try:
        await run_orderbook_stream(market_id, messages, ingestor, snapshot_provider, now_ms=messages_now_ms or now_ms)
    finally:
        snap_task.cancel()
        prune_task.cancel()
        with contextlib.suppress(Exception):
            await snap_task
        with contextlib.suppress(Exception):
            await prune_task
        # Final prune pass to enforce retention before exit
        try:
            threshold = now_ms() - retention_ms
            ingestor.prune_events_before(threshold)
        except Exception:
            pass
