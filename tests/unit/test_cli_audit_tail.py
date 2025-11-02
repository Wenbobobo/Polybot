from polybot.cli.commands import cmd_audit_tail
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_cli_audit_tail_outputs_rows(tmp_path):
    db = f"sqlite:///{(tmp_path/'a.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO exec_audit (ts_ms, plan_id, duration_ms, place_call_ms, ack_latency_ms, plan_rationale, expected_profit, intents_json, acks_json) VALUES (?,?,?,?,?,?,?,?,?)",
        (123, "pid", 10, 5, 5, "r", 0.0, "[]", "[]"),
    )
    con.commit()
    out = cmd_audit_tail(db_url=db, limit=1)
    lines = out.splitlines()
    assert lines[0].startswith("ts_ms plan_id")
    assert "pid" in lines[1]

