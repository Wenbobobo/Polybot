import sys

from polybot.storage.migrate import migrate


class _StubCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql):  # noqa: D401
        self.executed.append(sql)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _StubConn:
    def __init__(self):
        self.cur = _StubCursor()

    def cursor(self):  # noqa: D401
        return self.cur

    def commit(self):  # noqa: D401
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _StubPsycopgModule:
    def connect(self, url):  # noqa: D401
        return _StubConn()


def test_migrate_apply_with_stubbed_psycopg():
    sys.modules["psycopg"] = _StubPsycopgModule()
    try:
        out = migrate("postgresql://user:pass@host:5432/db", print_sql_only=False, apply=True)
    finally:
        sys.modules.pop("psycopg", None)
    assert out == "postgresql: migrations applied"
