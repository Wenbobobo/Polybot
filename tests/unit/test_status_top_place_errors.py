from pathlib import Path

from polybot.cli.commands import cmd_status_top
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset


def test_status_top_includes_place_errors(tmp_path: Path):
    dbfile = tmp_path / "t.db"
    con = connect_sqlite(f"sqlite:///{dbfile}")
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 1, 1000, 1, 0),
    )
    con.commit()
    reset()
    inc_labelled("relayer_place_errors", {"market": "m1"}, 3)
    out = cmd_status_top(db_url=f"sqlite:///{dbfile}", limit=1)
    assert out.splitlines()[0].startswith("market_id resync_ratio rejects place_errors builder_errors")
    # place_errors field is the 4th column
    parts = out.splitlines()[1].split()
    assert parts[3] == '3'
