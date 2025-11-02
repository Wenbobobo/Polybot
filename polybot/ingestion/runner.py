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
        # If a market field exists and doesn't match, ignore this message.
        if msg.get("market") not in (None, market_id):
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


async def run_orderbook_stream_with_reconnect(
    market_id: str,
    messages_factory: Callable[[], AsyncIterator[Dict[str, Any]]],
    ingestor: OrderbookIngestor,
    snapshot_provider: SnapshotProvider,
    now_ms: Optional[Callable[[], int]] = None,
    max_retries: int = 3,
    backoff_ms: int = 100,
    snapshot_throttle_ms: Optional[int] = None,
    sleep_ms: Optional[Callable[[int], None]] = None,
) -> None:
    """Run orderbook stream with reconnect/backoff and optional snapshot throttling.

    - On iterator exception/closure, re-create it up to `max_retries` with linear backoff.
    - If `snapshot_throttle_ms` is set, repeated resyncs within the window coalesce to a single snapshot fetch.
    """
    last_snapshot_ts: Optional[int] = None

    def throttled_snapshot() -> None:
        nonlocal last_snapshot_ts
        ts_now = now_ms() if now_ms else None
        if snapshot_throttle_ms is not None and ts_now is not None:
            if last_snapshot_ts is not None and ts_now - last_snapshot_ts < snapshot_throttle_ms:
                return
        snap = snapshot_provider.get_snapshot(market_id)
        snap.setdefault("type", "snapshot")
        ingestor.process(snap, ts_ms=ts_now)
        last_snapshot_ts = ts_now

    attempts = 0
    while attempts <= max_retries:
        try:
            # initial snapshot before consuming stream to ensure state
            throttled_snapshot()
            async for msg in messages_factory():
                typ = msg.get("type")
                if typ not in ("snapshot", "delta"):
                    continue
                ok, _ = validate_message(msg)
                if not ok:
                    inc("ingestion_msg_invalid")
                    inc_labelled("ingestion_msg_invalid", {"market": market_id})
                    continue
                if typ == "delta":
                    delta_seq = int(msg.get("seq", 0))
                    cur_seq = ingestor.assembler._seq
                    if cur_seq and delta_seq != cur_seq + 1:
                        throttled_snapshot()
                        inc("ingestion_resync_gap")
                        inc_labelled("ingestion_resync_gap", {"market": market_id})
                ts = now_ms() if now_ms else None
                ingestor.process(msg, ts_ms=ts)
                inc("ingestion_msg_applied")
                inc_labelled("ingestion_msg_applied", {"market": market_id})
                if typ == "delta" and "checksum" in msg:
                    book = ingestor.assembler
                    ob = book.apply_delta({"seq": book._seq})
                    local = orderbook_checksum(ob.bids, ob.asks)
                    if local != msg.get("checksum"):
                        throttled_snapshot()
                        inc("ingestion_resync_checksum")
                        inc_labelled("ingestion_resync_checksum", {"market": market_id})
            # normal exit
            break
        except Exception:
            attempts += 1
            if attempts > max_retries:
                break
            if sleep_ms:
                sleep_ms(backoff_ms * attempts)
            else:
                import time as _t

                _t.sleep((backoff_ms * attempts) / 1000.0)
