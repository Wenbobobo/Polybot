from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


def connect_sqlite(url: str) -> sqlite3.Connection:
    """Create a SQLite connection from a URL like sqlite:///./file.db or :memory:.

    Enables WAL if file-backed and requested elsewhere.
    """
    if url == ":memory:" or url.startswith("sqlite:///:memory"):
        path = ":memory:"
    elif url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
    else:
        raise ValueError(f"Unsupported SQLite URL: {url}")
    Path(path).parent.mkdir(parents=True, exist_ok=True) if path != ":memory:" else None
    con = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def enable_wal(con: sqlite3.Connection) -> None:
    try:
        con.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.DatabaseError:
        pass
