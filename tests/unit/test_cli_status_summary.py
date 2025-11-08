from polybot.cli.commands import cmd_status_summary
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.observability.metrics import inc_labelled, reset as metrics_reset


def test_status_summary_outputs_expected_columns(tmp_path):
    metrics_reset()
    db = f"sqlite:///{(tmp_path/'s.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO market_status (market_id, last_seq, last_update_ts_ms, snapshots, deltas) VALUES (?,?,?,?,?)",
        ("m1", 1, 100, 1, 1),
    )
    con.commit()
    # Seed metrics
    inc_labelled("ingestion_msg_applied", {"market": "m1"}, 10)
    inc_labelled("ingestion_resync_gap", {"market": "m1"}, 2)
    inc_labelled("relayer_acks_rejected", {"market": "m1"}, 1)
    inc_labelled("relayer_place_errors", {"market": "m1"}, 3)
    inc_labelled("service_market_runtime_ms_sum", {"market": "m1"}, 50)
    inc_labelled("service_market_runtime_count", {"market": "m1"}, 1)
    inc_labelled("relayer_builder_errors", {"market": "m1"}, 4)
    out = cmd_status_summary(db_url=db)
    lines = out.splitlines()
    assert lines[0] == "market_id resync_ratio rejects place_errors builder_errors runtime_avg_ms"
    # resync_ratio = (2 / 10) = 0.2
    assert lines[1].startswith("m1 ") and " 0.200 " in lines[1]
    assert " 4 " in lines[1]
