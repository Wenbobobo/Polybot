from pathlib import Path

from polybot.cli.commands import cmd_tgbot_run_local


def test_cli_tgbot_run_local(tmp_path: Path):
    updates = tmp_path / "updates.jsonl"
    updates.write_text('{"message":{"text":"/help"}}\n{"message":{"text":"/buy 0.5 1"}}', encoding="utf-8")
    out = cmd_tgbot_run_local(str(updates), market_id="m1", outcome_yes_id="yes", db_url=":memory:")
    assert "commands" in out and "ok:" in out

