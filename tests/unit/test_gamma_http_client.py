import httpx
from polybot.adapters.polymarket.gamma_http import GammaHttpClient


def test_gamma_http_client_lists_and_normalizes_markets():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/markets"
        payload = [
            {"id": "m1", "title": "T1", "status": "active", "outcomes": [{"id": "o1", "name": "Yes"}]}
        ]
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://gamma.example")

    ghc = GammaHttpClient(base_url="https://gamma.example", client=client)
    markets = ghc.list_markets()
    assert markets and markets[0]["market_id"] == "m1"

