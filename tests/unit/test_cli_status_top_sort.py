from polybot.cli.commands import cmd_status_top
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset as metrics_reset


def test_status_top_includes_place_errors_and_sorts(tmp_path):
    metrics_reset()
    db_url = f"sqlite:///{(tmp_path/'top.db').as_posix()}"
    con = connect_sqlite(db_url)
    schema.create_all(con)
    # Seed two markets in status
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 10, 1000, 1, 5),
    )
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m2", 10, 1000, 1, 5),
    )
    con.commit()
    # m2: worse resync ratio and errors
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 10)
    inc_labelled("ingestion_resync_gap", {"market": "m1"}, 1)
    inc_labelled("ingestion_msg_applied", {"market": "m2"}, 10)
    inc_labelled("ingestion_resync_gap", {"market": "m2"}, 3)
    inc_labelled("relayer_place_errors", {"market": "m2"}, 2)
    out = cmd_status_top(db_url=db_url, limit=2)
    # Header includes extended columns
    header = out.splitlines()[0]
    assert "place_errors" in header and "builder_errors" in header and "rate_limited_total" in header and "timeouts_total" in header
    # m2 should appear first due to higher resync ratio and place errors
    assert out.splitlines()[1].startswith("m2 ")
