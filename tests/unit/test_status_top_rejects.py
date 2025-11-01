from pathlib import Path

from polybot.cli.commands import cmd_status_top
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled


def test_status_top_includes_rejects(tmp_path: Path):
    dbfile = tmp_path / "t.db"
    con = connect_sqlite(f"sqlite:///{dbfile}")
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 1, 1000, 1, 0),
    )
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m2", 1, 1000, 1, 0),
    )
    con.commit()
    inc_labelled("relayer_acks_rejected", {"market": "m1"}, 5)
    inc_labelled("relayer_acks_rejected", {"market": "m2"}, 1)
    out = cmd_status_top(db_url=f"sqlite:///{dbfile}", limit=2)
    # First line is header; expect m1 to be listed above m2 due to higher rejects
    lines = out.splitlines()
    assert lines[0].startswith("market_id resync_ratio rejects")
    assert lines[1].startswith("m1 ")

