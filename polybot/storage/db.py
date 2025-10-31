from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple


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


def parse_db_url(url: str) -> Tuple[str, str]:
    """Parse a DB URL and return (scheme, target).

    Examples:
    - sqlite:///./file.db -> ("sqlite", "./file.db")
    - sqlite:///:memory: -> ("sqlite", ":memory:")
    - postgresql://user:pass@host:5432/db -> ("postgresql", full_url)
    - postgres://user@host/db -> ("postgresql", full_url)
    """
    if url == ":memory:" or url.startswith("sqlite:///:memory"):
        return ("sqlite", ":memory:")
    if url.startswith("sqlite:///"):
        return ("sqlite", url.replace("sqlite:///", "", 1))
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return ("postgresql", url)
    raise ValueError(f"Unsupported DB URL: {url}")


def connect(url: str) -> sqlite3.Connection:
    """Connect to a database based on URL.

    Currently supports SQLite; PostgreSQL path is reserved for future migration and will raise NotImplementedError.
    """
    scheme, target = parse_db_url(url)
    if scheme == "sqlite":
        return connect_sqlite(url)
    if scheme == "postgresql":
        # Placeholder for future PostgreSQL support
        raise NotImplementedError("PostgreSQL support is planned but not implemented in Phase 1")
    raise ValueError(f"Unsupported scheme: {scheme}")
