import pytest

from polybot.cli.commands import cmd_migrate


def test_migrate_apply_raises_when_psycopg_missing(monkeypatch):
    # Force import error by monkeypatching storage.migrate.psycopg import path
    with pytest.raises(NotImplementedError):
        cmd_migrate(db_url="postgresql://user:pass@localhost:5432/db", print_sql=False, apply=True)

