from pathlib import Path

from polybot.cli.commands import cmd_health, cmd_replay


def test_cmd_health_reports_ok_then_stale(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    file = tmp_path / "m1.jsonl"
    file.write_text('{"type":"snapshot","seq":10,"bids":[[0.4,1.0]],"asks":[[0.6,1.0]]}', encoding="utf-8")
    cmd_replay(str(file), market_id="m1", db_url=f"sqlite:///{dbfile}")
    out = cmd_health(db_url=f"sqlite:///{dbfile}", staleness_threshold_ms=10_000_000)
    assert out.startswith("OK:")
    # Force low threshold to mark as stale
    out2 = cmd_health(db_url=f"sqlite:///{dbfile}", staleness_threshold_ms=1)
    assert out2.startswith("STALE")

