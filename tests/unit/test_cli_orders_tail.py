import json
from polybot.cli.commands import cmd_orders_tail
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_cli_orders_tail_json_and_text(tmp_path):
    db = f"sqlite:///{(tmp_path/'o.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO orders (order_id, client_oid, market_id, outcome_id, side, price, size, tif, status, created_ts_ms) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("o1", "c1", "m1", "o", "buy", 0.4, 1.0, "IOC", "accepted", 1),
    )
    con.commit()
    out_text = cmd_orders_tail(db_url=db, limit=1, as_json=False)
    assert "order_id market_id" in out_text.splitlines()[0]
    out_json = cmd_orders_tail(db_url=db, limit=1, as_json=True)
    data = json.loads(out_json)
    assert data and data[0]["order_id"] == "o1"

