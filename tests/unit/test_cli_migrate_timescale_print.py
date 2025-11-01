from polybot.cli.commands import cmd_migrate_timescale_print


def test_migrate_timescale_print_outputs_sql():
    out = cmd_migrate_timescale_print()
    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in out

