from pathlib import Path

from polybot.cli.commands import cmd_status_watch, cmd_replay


def test_cmd_status_watch_outputs_multiple_snapshots(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    # seed with a snapshot via replay
    file = tmp_path / "m1.jsonl"
    file.write_text('{"type":"snapshot","seq":10,"bids":[[0.4,1.0]],"asks":[[0.6,1.0]]}', encoding="utf-8")
    cmd_replay(str(file), market_id="m1", db_url=f"sqlite:///{dbfile}")
    out = cmd_status_watch(db_url=f"sqlite:///{dbfile}", interval_ms=10, iterations=2)
    assert out.count("market_id") >= 2

