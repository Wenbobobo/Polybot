import httpx

from polybot.cli.commands import cmd_refresh_markets_with_client
from polybot.storage.db import connect_sqlite


def test_cli_refresh_markets_with_mock_client(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/markets":
            payload = [
                {"id": "m1", "title": "T1", "status": "active", "outcomes": [{"id": "o1", "name": "Yes"}]}
            ]
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://gamma.example")
    dbfile = tmp_path / "test.db"
    n = cmd_refresh_markets_with_client(client, base_url="https://gamma.example", db_url=f"sqlite:///{dbfile}")
    assert n == 1
    con = connect_sqlite(f"sqlite:///{dbfile}")
    c = con.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    assert c == 1

