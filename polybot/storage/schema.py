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
    "outcomes": (
        """
        CREATE TABLE IF NOT EXISTS outcomes (
            outcome_id TEXT PRIMARY KEY,
            market_id TEXT NOT NULL,
            name TEXT NOT NULL,
            tick_size REAL NOT NULL DEFAULT 0.01,
            min_size REAL NOT NULL DEFAULT 1.0,
            FOREIGN KEY (market_id) REFERENCES markets(market_id)
        );
        CREATE INDEX IF NOT EXISTS idx_outcomes_market ON outcomes(market_id);
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
    "orderbook_snapshots": (
        """
        CREATE TABLE IF NOT EXISTS orderbook_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            ts_ms INTEGER NOT NULL,
            seq INTEGER NOT NULL,
            best_bid REAL,
            best_ask REAL,
            mid REAL,
            checksum TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_obs_market_ts ON orderbook_snapshots(market_id, ts_ms);
        """
    ),
    "orders": (
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            client_oid TEXT,
            market_id TEXT NOT NULL,
            outcome_id TEXT NOT NULL,
            side TEXT NOT NULL CHECK (side IN ('buy','sell')),
            price REAL NOT NULL,
            size REAL NOT NULL,
            tif TEXT NOT NULL,
            status TEXT NOT NULL,
            created_ts_ms INTEGER NOT NULL,
            updated_ts_ms INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_orders_market ON orders(market_id);
        CREATE INDEX IF NOT EXISTS idx_orders_market_status ON orders(market_id, status);
        """
    ),
    "fills": (
        """
        CREATE TABLE IF NOT EXISTS fills (
            fill_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            ts_ms INTEGER NOT NULL,
            price REAL NOT NULL,
            size REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        CREATE INDEX IF NOT EXISTS idx_fills_order ON fills(order_id);
        """
    ),
    "market_status": (
        """
        CREATE TABLE IF NOT EXISTS market_status (
            market_id TEXT PRIMARY KEY,
            last_seq INTEGER NOT NULL DEFAULT 0,
            last_update_ts_ms INTEGER NOT NULL DEFAULT 0,
            snapshots INTEGER NOT NULL DEFAULT 0,
            deltas INTEGER NOT NULL DEFAULT 0
        );
        """
    ),
    "exec_audit": (
        """
        CREATE TABLE IF NOT EXISTS exec_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_ms INTEGER NOT NULL,
            plan_id TEXT,
            duration_ms INTEGER,
            plan_rationale TEXT,
            expected_profit REAL,
            intents_json TEXT,
            acks_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_exec_audit_ts ON exec_audit(ts_ms);
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
