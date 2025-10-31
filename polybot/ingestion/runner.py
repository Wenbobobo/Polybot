from __future__ import annotations

from typing import AsyncIterator, Dict, Any

from .orderbook import OrderbookIngestor
from .snapshot import SnapshotProvider


async def run_orderbook_stream(
    market_id: str,
    messages: AsyncIterator[Dict[str, Any]],
    ingestor: OrderbookIngestor,
    snapshot_provider: SnapshotProvider,
) -> None:
    """Process an async stream of orderbook messages with resync logic.

    Rules:
    - If first message is delta or when a seq gap is detected, obtain a fresh snapshot
      and apply it before continuing.
    - Duplicate/older seq deltas are ignored (assembler handles monotonic checks).
    """

    first_seen = True
    async for msg in messages:
        typ = msg.get("type")
        if typ not in ("snapshot", "delta"):
            continue

        if first_seen and typ != "snapshot":
            snap = snapshot_provider.get_snapshot(market_id)
            snap.setdefault("type", "snapshot")
            ingestor.process(snap)
            first_seen = False

        if typ == "delta":
            # check seq gap
            delta_seq = int(msg.get("seq", 0))
            cur_seq = ingestor.assembler._seq  # internal state; safe for our use
            if cur_seq and delta_seq != cur_seq + 1:
                snap = snapshot_provider.get_snapshot(market_id)
                snap.setdefault("type", "snapshot")
                ingestor.process(snap)

        ingestor.process(msg)
        first_seen = False

