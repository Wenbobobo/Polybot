from pathlib import Path
from polybot.cli.commands import cmd_status
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_status_verbose_includes_quote_metrics(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    con = connect_sqlite(f"sqlite:///{dbfile}")
    schema.create_all(con)
    # Seed a fake market_status row
    con.execute("INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)", ("m1", 1, 1000, 1, 0))
    con.commit()
    out = cmd_status(db_url=f"sqlite:///{dbfile}", verbose=True)
    assert "quotes:" in out and "orders:" in out

