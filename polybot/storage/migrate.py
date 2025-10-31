from __future__ import annotations

from pathlib import Path
from typing import Optional

from .db import parse_db_url
from . import schema as sqlite_schema


def migrate(db_url: str, print_sql_only: bool = False, apply: bool = False) -> str:
    """Run or print migrations based on db URL.

    - SQLite: schema is applied by service/CLI init; returns summary.
    - PostgreSQL: reads migrations/postgres/001_init.sql; with print_sql_only returns SQL; with apply attempts to apply via psycopg.
    """
    scheme, _ = parse_db_url(db_url)
    if scheme == "sqlite":
        return "sqlite: create_all() is handled by service/CLI init"
    if scheme == "postgresql":
        sql = Path("migrations/postgres/001_init.sql").read_text(encoding="utf-8")
        if print_sql_only and not apply:
            return sql
        if apply:
            try:
                import psycopg
            except Exception as e:  # noqa: BLE001
                raise NotImplementedError("psycopg not installed; cannot apply migrations") from e
            # Apply in a single transaction
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            return "postgresql: migrations applied"
        # default: neither print nor apply
        return "postgresql: set --print-sql to view or --apply to execute"
    raise ValueError(f"Unsupported scheme for migration: {scheme}")
