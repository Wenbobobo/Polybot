from polybot.storage.db import parse_db_url, connect


def test_parse_db_url_sqlite_and_postgres():
    s = parse_db_url("sqlite:///./x.db")
    assert s[0] == "sqlite"
    p = parse_db_url("postgresql://user:pass@localhost:5432/db")
    assert p[0] == "postgresql"


def test_connect_sqlite_and_postgres_not_implemented(tmp_path):
    con = connect(f"sqlite:///{tmp_path/'t.db'}")
    cur = con.execute("select 1")
    assert cur.fetchone()[0] == 1
    try:
        connect("postgresql://user:pass@localhost:5432/db")
        assert False, "postgres should raise until implemented"
    except NotImplementedError:
        pass

