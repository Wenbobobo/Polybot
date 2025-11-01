from polybot.cli import commands as cmds


def test_cli_dry_run_validates_private_key():
    out = cmds.cmd_relayer_dry_run("m", "o", "buy", 0.4, 1.0, base_url="u", private_key="bad")
    assert out.startswith("invalid private_key")

