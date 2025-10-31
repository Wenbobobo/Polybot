from __future__ import annotations

from typing import AsyncIterator, Dict, Any, Optional, Callable

from .orderbook import OrderbookIngestor
from .snapshot import SnapshotProvider
from polybot.core.checksum import orderbook_checksum
from .validator import validate_message
from polybot.observability.metrics import inc, inc_labelled


async def run_orderbook_stream(
    market_id: str,
    messages: AsyncIterator[Dict[str, Any]],
    ingestor: OrderbookIngestor,
    snapshot_provider: SnapshotProvider,
    now_ms: Optional[Callable[[], int]] = None,
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
        ok, reason = validate_message(msg)
        if not ok:
            inc("ingestion_msg_invalid")
            inc_labelled("ingestion_msg_invalid", {"market": market_id})
            continue

        if first_seen and typ != "snapshot":
            snap = snapshot_provider.get_snapshot(market_id)
            snap.setdefault("type", "snapshot")
            ts = now_ms() if now_ms else None
            ingestor.process(snap, ts_ms=ts)
            inc("ingestion_resync_first_delta")
            inc_labelled("ingestion_resync_first_delta", {"market": market_id})
            first_seen = False

        if typ == "delta":
            # check seq gap
            delta_seq = int(msg.get("seq", 0))
            cur_seq = ingestor.assembler._seq  # internal state; safe for our use
            if cur_seq and delta_seq != cur_seq + 1:
                snap = snapshot_provider.get_snapshot(market_id)
                snap.setdefault("type", "snapshot")
                ts = now_ms() if now_ms else None
                ingestor.process(snap, ts_ms=ts)
                inc("ingestion_resync_gap")
                inc_labelled("ingestion_resync_gap", {"market": market_id})

        ts = now_ms() if now_ms else None
        ingestor.process(msg, ts_ms=ts)
        inc("ingestion_msg_applied")
        inc_labelled("ingestion_msg_applied", {"market": market_id})
        # Optional checksum verification on delta messages
        if typ == "delta" and "checksum" in msg:
            book = ingestor.assembler
            # materialize current OrderBook
            ob = book.apply_delta({"seq": book._seq})
            bb = ob.bids
            aa = ob.asks
            local = orderbook_checksum(bb, aa)
            if local != msg.get("checksum"):
                snap = snapshot_provider.get_snapshot(market_id)
                snap.setdefault("type", "snapshot")
                ts2 = now_ms() if now_ms else None
                ingestor.process(snap, ts_ms=ts2)
                inc("ingestion_resync_checksum")
                inc_labelled("ingestion_resync_checksum", {"market": market_id})
        first_seen = False
