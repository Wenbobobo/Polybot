from __future__ import annotations

import sqlite3


DDL = {
    "markets": (
        """
        CREATE TABLE IF NOT EXISTS markets (
            market_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            condition_id TEXT,
            neg_risk_group TEXT,
            rule_hash TEXT
        );
        """
    ),
    "orderbook_events": (
        """
        CREATE TABLE IF NOT EXISTS orderbook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            ts_ms INTEGER NOT NULL,
            side TEXT NOT NULL CHECK (side IN ('bid','ask')),
            price REAL NOT NULL,
            size_delta REAL NOT NULL,
            op TEXT,
            CHECK (price >= 0.0)
        );
        CREATE INDEX IF NOT EXISTS idx_obe_market_ts ON orderbook_events(market_id, ts_ms);
        CREATE UNIQUE INDEX IF NOT EXISTS u_obe_market_seq_id ON orderbook_events(market_id, seq, id);
        """
    ),
}


def create_all(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    for ddl in DDL.values():
        cur.executescript(ddl)
    con.commit()


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
    return cur.fetchone() is not None

