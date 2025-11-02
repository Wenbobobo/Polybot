from polybot.cli.commands import cmd_status
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset as metrics_reset


def test_status_verbose_includes_ack_avg_ms(tmp_path):
    metrics_reset()
    db_url = f"sqlite:///{(tmp_path/'s.db').as_posix()}"
    con = connect_sqlite(db_url)
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 1, 100, 1, 1),
    )
    con.commit()
    # Seed metrics
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 1)
    inc_labelled("engine_execute_plan_ms_sum", {"market": "m1"}, 10)
    inc_labelled("engine_execute_plan_count", {"market": "m1"}, 1)
    inc_labelled("engine_ack_ms_sum", {"market": "m1"}, 7)
    inc_labelled("engine_ack_count", {"market": "m1"}, 1)
    out = cmd_status(db_url=db_url, verbose=True)
    assert "ack_avg_ms=7.0" in out

