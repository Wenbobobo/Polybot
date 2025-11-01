from polybot.cli.commands import cmd_conversions_merge, cmd_conversions_split


def test_cli_conversions_merge_and_split():
    out1 = cmd_conversions_merge("m1", "y", "n", 5.0)
    assert out1.startswith("merge accepted=")
    out2 = cmd_conversions_split("m1", "y", "n", 2.5)
    assert out2.startswith("split accepted=")

