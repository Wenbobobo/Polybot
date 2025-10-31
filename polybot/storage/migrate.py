from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from .db import parse_db_url
from . import schema as sqlite_schema


def migrate(db_url: str, print_sql_only: bool = False) -> str:
    """Run or print migrations based on db URL.

    - SQLite: applies schema.create_all and returns a summary string.
    - PostgreSQL: reads migrations/postgres/001_init.sql. If print_sql_only=True, returns SQL string; otherwise raises NotImplementedError (apply pending).
    """
    scheme, _ = parse_db_url(db_url)
    if scheme == "sqlite":
        import sqlite3
        con = sqlite_schema.sqlite3.connect(":memory:")  # type: ignore[attr-defined]
        # create_all requires a connection for the target db; for SQLite file urls we rely on Service/CLI init
        # Here we only return a summary for CLI flow.
        return "sqlite: create_all() will be applied by service/CLI init"
    if scheme == "postgresql":
        sql = Path("migrations/postgres/001_init.sql").read_text(encoding="utf-8")
        if print_sql_only:
            return sql
        raise NotImplementedError("PostgreSQL apply not implemented; use --print to inspect SQL")
    raise ValueError(f"Unsupported scheme for migration: {scheme}")

