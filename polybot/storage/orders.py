from __future__ import annotations

import json
import time
import sqlite3
from typing import List

from polybot.adapters.polymarket.relayer import OrderAck
from polybot.exec.planning import OrderIntent


def persist_orders_and_fills(con: sqlite3.Connection, intents: List[OrderIntent], acks: List[OrderAck]) -> None:
    ts_ms = int(time.time() * 1000)
    for i, ack in enumerate(acks):
        intent = intents[i]
        status = ack.status
        con.execute(
            """
            INSERT INTO orders (order_id, client_oid, market_id, outcome_id, side, price, size, tif, status, created_ts_ms, updated_ts_ms)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(order_id) DO UPDATE SET status=excluded.status, updated_ts_ms=excluded.updated_ts_ms
            """,
            (
                ack.order_id,
                intent.client_order_id,
                intent.market_id,
                intent.outcome_id,
                intent.side,
                intent.price,
                intent.size,
                intent.tif,
                status,
                ts_ms,
                ts_ms,
            ),
        )
        if ack.filled_size and ack.filled_size > 0:
            fill_id = f"{ack.order_id}-f1"
            con.execute(
                "INSERT INTO fills (fill_id, order_id, ts_ms, price, size, fee) VALUES (?,?,?,?,?,?)",
                (fill_id, ack.order_id, ts_ms, intent.price, ack.filled_size, 0.0),
            )
    con.commit()

