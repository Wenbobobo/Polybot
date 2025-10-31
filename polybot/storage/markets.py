from __future__ import annotations

import sqlite3
from typing import List, Dict, Any


def upsert_markets(con: sqlite3.Connection, markets: List[Dict[str, Any]]) -> None:
    cur = con.cursor()
    for m in markets:
        cur.execute(
            "INSERT INTO markets (market_id, title, status, condition_id, neg_risk_group, rule_hash) VALUES (?,?,?,?,?,?)\n"
            "ON CONFLICT(market_id) DO UPDATE SET title=excluded.title, status=excluded.status",
            (m.get("market_id"), m.get("title"), m.get("status"), m.get("condition_id"), m.get("neg_risk_group"), m.get("rule_hash")),
        )
        for o in m.get("outcomes", []) or []:
            cur.execute(
                "INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)\n"
                "ON CONFLICT(outcome_id) DO UPDATE SET name=excluded.name",
                (o.get("outcome_id"), m.get("market_id"), o.get("name"), o.get("tick_size", 0.01), o.get("min_size", 1.0)),
            )
    con.commit()

