from __future__ import annotations

from typing import Protocol, List, Dict, Any
import sqlite3

from polybot.storage.markets import upsert_markets


class GammaClientProto(Protocol):
    def list_markets(self) -> List[Dict[str, Any]]: ...


def refresh_markets(con: sqlite3.Connection, gamma_client: GammaClientProto) -> int:
    markets = gamma_client.list_markets()
    upsert_markets(con, markets)
    return len(markets)

