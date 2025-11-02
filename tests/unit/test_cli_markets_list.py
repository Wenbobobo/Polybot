import json
from polybot.cli.commands import cmd_markets_list
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_cmd_markets_list_json(tmp_path):
    db = f"sqlite:///{(tmp_path/'m.db').as_posix()}"
    con = connect_sqlite(db)
    schema.create_all(con)
    con.execute(
        "INSERT INTO markets (market_id, title, status) VALUES (?,?,?)",
        ("m1", "Test Market", "active"),
    )
    con.execute(
        "INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)",
        ("yes", "m1", "Yes", 0.01, 1.0),
    )
    con.execute(
        "INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)",
        ("no", "m1", "No", 0.01, 1.0),
    )
    con.commit()
    out = cmd_markets_list(db_url=db, limit=5, as_json=True)
    data = json.loads(out)
    assert isinstance(data, list) and data and data[0]["market_id"] == "m1"
    assert set(o["outcome_id"] for o in data[0]["outcomes"]) == {"yes", "no"}

