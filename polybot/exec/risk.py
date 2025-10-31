from __future__ import annotations

import sqlite3
from typing import Tuple
from polybot.exec.planning import ExecutionPlan


def compute_inventory(con: sqlite3.Connection, market_id: str, outcome_id: str) -> float:
    cur = con.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN o.side='buy' THEN f.size ELSE -f.size END), 0.0)
        FROM fills f JOIN orders o ON f.order_id=o.order_id
        WHERE o.market_id=? AND o.outcome_id=?
        """,
        (market_id, outcome_id),
    )
    row = cur.fetchone()
    return float(row[0] if row and row[0] is not None else 0.0)


def will_exceed_exposure(con: sqlite3.Connection, plan: ExecutionPlan, cap_per_outcome: float) -> Tuple[bool, float]:
    # Aggregate intents by outcome with sign (buy +, sell -)
    pend: dict[Tuple[str, str], float] = {}
    for it in plan.intents:
        key = (it.market_id, it.outcome_id)
        signed = it.size if it.side == "buy" else -it.size
        pend[key] = pend.get(key, 0.0) + signed
    # Check each outcome
    for (mid, oid), delta in pend.items():
        inv = compute_inventory(con, mid, oid)
        if abs(inv + delta) > cap_per_outcome:
            return True, inv
    return False, 0.0

