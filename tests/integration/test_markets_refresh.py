import httpx

from polybot.ingestion.markets import refresh_markets
from polybot.adapters.polymarket.gamma_http import GammaHttpClient
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_refresh_markets_upserts_into_db():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/markets":
            payload = [
                {"id": "m1", "title": "T1", "status": "active", "outcomes": [{"id": "o1", "name": "Yes"}]},
                {"id": "m2", "title": "T2", "status": "active", "outcomes": [{"id": "o2", "name": "A"}, {"id": "o3", "name": "B"}]},
            ]
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://gamma.example")
    ghc = GammaHttpClient(base_url="https://gamma.example", client=client)

    con = connect_sqlite(":memory:")
    schema.create_all(con)
    n = refresh_markets(con, ghc)
    assert n == 2
    m = con.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    o = con.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
    assert m == 2 and o == 3

