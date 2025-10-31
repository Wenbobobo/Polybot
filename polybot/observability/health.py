from __future__ import annotations

import sqlite3
from typing import List, Dict, Any


def check_staleness(con: sqlite3.Connection, threshold_ms: int) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    rows = con.execute("SELECT market_id, last_update_ts_ms FROM market_status").fetchall()
    if not rows:
        return issues
    # Allow zero threshold to disable
    if threshold_ms <= 0:
        return issues
    import time

    now_ms = int(time.time() * 1000)
    for mkt, ts in rows:
        if ts and now_ms - int(ts) > threshold_ms:
            issues.append({"market_id": mkt, "age_ms": now_ms - int(ts)})
    return issues

