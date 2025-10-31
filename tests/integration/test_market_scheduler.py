import asyncio
import httpx
import pytest

from polybot.ingestion.market_scheduler import run_market_refresh_loop
from polybot.adapters.polymarket.gamma_http import GammaHttpClient
from polybot.storage.db import connect_sqlite
from polybot.storage import schema


@pytest.mark.asyncio
async def test_market_refresh_loop_runs_iterations():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/markets":
            return httpx.Response(200, json=[{"id": "m1", "title": "T1", "status": "active", "outcomes": []}])
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://gamma.example")
    ghc = GammaHttpClient(base_url="https://gamma.example", client=client)
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    await run_market_refresh_loop(con, ghc, interval_ms=10, iterations=2)
    cnt = con.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    assert cnt == 1

