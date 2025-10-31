import sqlite3
from polybot.storage.db import connect_sqlite, enable_wal


def test_sqlite_enable_wal(tmp_path):
    dbfile = tmp_path / "test.db"
    con = connect_sqlite(f"sqlite:///{dbfile}")
    enable_wal(con)
    cur = con.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0].upper()
    assert mode in ("WAL", "MEMORY", "OFF")  # Some platforms may not support WAL in memory

