import json
from polybot.cli.commands import cmd_status, cmd_status_summary
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset as metrics_reset


def test_cmd_status_returns_json(tmp_path):
    metrics_reset()
    db = f"sqlite:///{(tmp_path/'j.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 10, 1000, 1, 5),
    )
    con.commit()
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 10)
    out = cmd_status(db_url=db, verbose=False, as_json=True)
    data = json.loads(out)
    assert isinstance(data, list) and data and data[0]["market_id"] == "m1"


def test_cmd_status_summary_returns_json(tmp_path):
    metrics_reset()
    db = f"sqlite:///{(tmp_path/'k.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 10, 1000, 1, 5),
    )
    con.commit()
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 10)
    out = cmd_status_summary(db_url=db, as_json=True)
    data = json.loads(out)
    assert isinstance(data, list) and data and data[0]["market_id"] == "m1"

