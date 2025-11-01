from pathlib import Path

from polybot.cli.commands import cmd_status
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset


def test_status_verbose_includes_engine_retries(tmp_path: Path):
    dbfile = tmp_path / "t.db"
    con = connect_sqlite(f"sqlite:///{dbfile}")
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 1, 1000, 1, 0),
    )
    con.commit()
    reset()
    inc_labelled("engine_retries", {"market": "m1"}, 3)
    out = cmd_status(db_url=f"sqlite:///{dbfile}", verbose=True)
    assert "retries=3" in out

