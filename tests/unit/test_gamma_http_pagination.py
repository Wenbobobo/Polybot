import httpx
from polybot.adapters.polymarket.gamma_http import GammaHttpClient


def test_gamma_http_pagination_envelope():
    pages = [
        {"data": [{"id": "m1", "title": "T1", "status": "active", "outcomes": []}], "next": "abc"},
        {"data": [{"id": "m2", "title": "T2", "status": "active", "outcomes": []}]},
    ]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = calls["n"]
        calls["n"] += 1
        return httpx.Response(200, json=pages[idx])

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://gamma.example")
    ghc = GammaHttpClient(base_url="https://gamma.example", client=client)
    ms = ghc.list_markets()
    ids = sorted([m["market_id"] for m in ms])
    assert ids == ["m1", "m2"]

