import asyncio

import pytest

from polybot.cli.commands import cmd_dutch_run_replay_async
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


@pytest.mark.asyncio
async def test_allow_other_true_enables_plan(tmp_path):
    dbfile = tmp_path / "test.db"
    con = connect_sqlite(f"sqlite:///{dbfile.as_posix()}")
    schema.create_all(con)
    con.execute("INSERT INTO markets (market_id, title, status) VALUES (?,?,?)", ("m1", "T", "active"))
    con.execute("INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)", ("o1", "m1", "Other", 0.01, 1.0))
    con.execute("INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)", ("o2", "m1", "B", 0.01, 1.0))
    con.commit()
    # Build events with sum asks < 1
    import json
    lines = [
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.49, 10.0]], "outcome_id": "o1"},
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.49, 10.0]], "outcome_id": "o2"},
    ]
    js = tmp_path / "events.jsonl"
    js.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    # Should run without errors when allow_other=True
    await cmd_dutch_run_replay_async(str(js), "m1", None, db_url=f"sqlite:///{dbfile.as_posix()}", allow_other=True)

