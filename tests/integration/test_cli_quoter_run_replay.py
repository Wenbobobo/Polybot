from pathlib import Path
from polybot.cli.commands import cmd_quoter_run_replay_async
from polybot.storage.db import connect_sqlite
import asyncio


def test_quoter_run_replay_places_orders(tmp_path: Path):
    file = tmp_path / "events.jsonl"
    file.write_text('\n'.join([
        '{"type":"snapshot","seq":1,"bids":[[0.4,100.0]],"asks":[[0.47,100.0]]}',
        '{"type":"delta","seq":2}',
        '{"type":"delta","seq":3,"bids":[[0.41,10.0]]}',
    ]), encoding="utf-8")
    dbfile = tmp_path / "test.db"

    asyncio.run(cmd_quoter_run_replay_async(str(file), market_id="m1", outcome_yes_id="yes", db_url=f"sqlite:///{dbfile}"))
    con = connect_sqlite(f"sqlite:///{dbfile}")
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt >= 2

