import json
from polybot.cli.commands import cmd_status
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset as metrics_reset


def test_cmd_status_json_verbose_includes_relayer_events(tmp_path):
    metrics_reset()
    db = f"sqlite:///{(tmp_path/'status.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 10, 1234, 1, 2),
    )
    con.commit()
    # Some baseline ingestion counters
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 10)
    # Relayer per-market events
    inc_labelled("relayer_rate_limited_events", {"market": "m1"}, 2)
    inc_labelled("relayer_timeouts_events", {"market": "m1"}, 1)
    inc_labelled("relayer_builder_errors", {"market": "m1"}, 4)

    out = cmd_status(db_url=db, verbose=True, as_json=True)
    data = json.loads(out)
    assert isinstance(data, list) and data and data[0]["market_id"] == "m1"
    assert data[0]["relayer_rate_limited_events"] == 2
    assert data[0]["relayer_timeouts_events"] == 1
    assert data[0]["relayer_builder_errors"] == 4
