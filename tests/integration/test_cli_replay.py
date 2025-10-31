from pathlib import Path

from polybot.cli.commands import cmd_replay
from polybot.storage.db import connect_sqlite


def test_cli_cmd_replay(tmp_path: Path):
    file = tmp_path / "m1.jsonl"
    file.write_text(
        "\n".join(
            [
                '{"type":"snapshot","seq":10,"bids":[[0.4,100.0]],"asks":[[0.47,50.0]]}',
                '{"type":"delta","seq":11,"bids":[[0.41,20.0]]}',
            ]
        ),
        encoding="utf-8",
    )
    dbfile = tmp_path / "test.db"
    cmd_replay(str(file), market_id="m1", db_url=f"sqlite:///{dbfile}")

    con = connect_sqlite(f"sqlite:///{dbfile}")
    cur = con.execute("SELECT COUNT(*) FROM orderbook_snapshots WHERE market_id='m1'")
    assert cur.fetchone()[0] == 1
    cur = con.execute("SELECT COUNT(*) FROM orderbook_events WHERE market_id='m1'")
    assert cur.fetchone()[0] == 1

