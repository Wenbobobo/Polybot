import json
from pathlib import Path

from polybot.cli import commands as cmds


def test_cli_config_dump_redacts_private_key(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        base_url = "https://clob.polymarket.com"
        private_key = "0x1111111111111111111111111111111111111111111111111111111111111111"
        chain_id = 137

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        subscribe = false
        max_messages = 1
        """,
        encoding="utf-8",
    )
    out = cmds.cmd_config_dump(str(cfg))
    data = json.loads(out)
    assert data["relayer"]["private_key"] == "***redacted***"

