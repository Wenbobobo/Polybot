from pathlib import Path

from polybot.cli.commands import cmd_preflight


def test_preflight_ok_with_fake_relayer(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "fake"

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        subscribe = false
        max_messages = 1
        """,
        encoding="utf-8",
    )
    out = cmd_preflight(str(cfg))
    assert out.startswith("OK:")


def test_preflight_invalid_private_key_for_real(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        private_key = "bad"

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        subscribe = false
        max_messages = 1
        """,
        encoding="utf-8",
    )
    out = cmd_preflight(str(cfg))
    assert out.startswith("INVALID:") and "private_key" in out

