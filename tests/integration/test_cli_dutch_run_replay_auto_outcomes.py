import asyncio
import json
from pathlib import Path

from polybot.cli.commands import cmd_dutch_run_replay_async
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_cli_dutch_run_replay_auto_outcomes(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    con = connect_sqlite(f"sqlite:///{dbfile.as_posix()}")
    schema.create_all(con)
    con.execute("INSERT INTO markets (market_id, title, status) VALUES (?,?,?)", ("m1", "T", "active"))
    for oid in ("o1", "o2", "o3"):
        con.execute("INSERT INTO outcomes (outcome_id, market_id, name, tick_size, min_size) VALUES (?,?,?,?,?)", (oid, "m1", "X", 0.01, 1.0))
    con.commit()
    lines = [
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o1"},
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o2"},
        {"type": "snapshot", "seq": 1, "bids": [], "asks": [[0.32, 10.0]], "outcome_id": "o3"},
    ]
    js = tmp_path / "msgs.jsonl"
    js.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")

    async def run():
        await cmd_dutch_run_replay_async(str(js), "m1", None, db_url=f"sqlite:///{dbfile.as_posix()}", min_profit_usdc=0.02, default_size=1.0, safety_margin_usdc=0.0)

    asyncio.run(run())
    # No assertion; ensure no exceptions and path runs end-to-end
    assert dbfile.exists()
