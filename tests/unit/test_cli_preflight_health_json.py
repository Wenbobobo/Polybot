import json
from pathlib import Path

from polybot.cli import commands as cmds


def test_preflight_json_ok(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        subscribe = false
        max_messages = 1
        """,
        encoding="utf-8",
    )
    out = cmds.cmd_preflight(str(cfg), as_json=True)
    data = json.loads(out)
    assert data.get("ok") is True


def test_health_json_ok(tmp_path: Path):
    # empty DB has no market_status; treat as ok True
    out = cmds.cmd_health(db_url=":memory:", as_json=True)
    data = json.loads(out)
    assert "ok" in data

