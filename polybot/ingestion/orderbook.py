from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict

import sqlite3

from polybot.adapters.polymarket.orderbook import OrderbookAssembler


@dataclass
class IngestionStats:
    applied: int = 0
    snapshots: int = 0


class OrderbookIngestor:
    def __init__(self, con: sqlite3.Connection, market_id: str):
        self.con = con
        self.market_id = market_id
        self.assembler = OrderbookAssembler(market_id)
        self.last_update_ts_ms: int = 0
        self.stats = IngestionStats()

    def process(self, msg: Dict[str, Any], ts_ms: int | None = None) -> None:
        ts_ms = ts_ms or int(time.time() * 1000)
        typ = msg.get("type")
        if typ == "snapshot":
            book = self.assembler.apply_snapshot(msg)
            bb = book.best_bid()
            ba = book.best_ask()
            best_bid = bb.price if bb else None
            best_ask = ba.price if ba else None
            mid = (best_bid + best_ask) / 2.0 if (best_bid is not None and best_ask is not None) else None
            checksum = f"b{len(msg.get('bids') or [])}a{len(msg.get('asks') or [])}"
            self.con.execute(
                "INSERT INTO orderbook_snapshots (market_id, ts_ms, seq, best_bid, best_ask, mid, checksum) VALUES (?,?,?,?,?,?,?)",
                (self.market_id, ts_ms, book.seq, best_bid, best_ask, mid, checksum),
            )
            self.stats.snapshots += 1
        elif typ == "delta":
            book = self.assembler.apply_delta(msg)
            # Persist each bid/ask change in msg to events table
            for side in ("bids", "asks"):
                for price, size_delta in msg.get(side, []) or []:
                    self.con.execute(
                        "INSERT INTO orderbook_events (market_id, seq, ts_ms, side, price, size_delta, op) VALUES (?,?,?,?,?,?,?)",
                        (
                            self.market_id,
                            book.seq,
                            ts_ms,
                            "bid" if side == "bids" else "ask",
                            float(price),
                            float(size_delta),
                            None,
                        ),
                    )
            self.stats.applied += 1
        else:
            # ignore unknown types
            return
        self.last_update_ts_ms = ts_ms
        # Update market_status
        self.con.execute(
            """
            INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(market_id) DO UPDATE SET
                last_seq=excluded.last_seq,
                last_update_ts_ms=excluded.last_update_ts_ms,
                snapshots=market_status.snapshots + (excluded.snapshots - market_status.snapshots),
                deltas=market_status.deltas + (excluded.deltas - market_status.deltas)
            """,
            (
                self.market_id,
                self.assembler._seq,
                self.last_update_ts_ms,
                self.stats.snapshots,
                self.stats.applied,
            ),
        )
        self.con.commit()

    def persist_snapshot_now(self, ts_ms: int) -> None:
        book = self.assembler
        # derive best levels from current state
        ob = book.apply_delta({"seq": book._seq})  # no-op delta to materialize current OrderBook
        bb = ob.best_bid()
        ba = ob.best_ask()
        best_bid = bb.price if bb else None
        best_ask = ba.price if ba else None
        mid = (best_bid + best_ask) / 2.0 if (best_bid is not None and best_ask is not None) else None
        self.con.execute(
            "INSERT INTO orderbook_snapshots (market_id, ts_ms, seq, best_bid, best_ask, mid, checksum) VALUES (?,?,?,?,?,?,?)",
            (self.market_id, ts_ms, ob.seq, best_bid, best_ask, mid, None),
        )
        self.stats.snapshots += 1
        self.con.commit()

    def prune_events_before(self, ts_ms_threshold: int) -> int:
        cur = self.con.execute("DELETE FROM orderbook_events WHERE ts_ms < ? AND market_id = ?", (ts_ms_threshold, self.market_id))
        self.con.commit()
        return cur.rowcount
