from types import SimpleNamespace

from polybot.adapters.polymarket.clob_http import ClobHttpClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeHttpxClient:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/price":
            return FakeResponse({"side": params.get("side"), "price": "0.42"})
        if path == "/midpoint":
            return FakeResponse({"midpoint": "0.50"})
        if path == "/spread":
            return FakeResponse({"spread": "0.08"})
        return FakeResponse({})


def test_clob_http_price_and_midpoint_calls_expected_paths():
    fake = FakeHttpxClient()
    client = ClobHttpClient(base_url="https://clob", client=fake)
    out_buy = client.get_price("tok", side="buy")
    out_mid = client.get_midpoint("tok")
    out_spread = client.get_spread("tok")
    assert fake.calls[0] == ("/price", {"token_id": "tok", "side": "BUY"})
    assert fake.calls[1] == ("/midpoint", {"token_id": "tok"})
    assert fake.calls[2] == ("/spread", {"token_id": "tok"})
    assert out_buy["side"] == "BUY"
    assert out_mid["midpoint"] == "0.50"
    assert out_spread["spread"] == "0.08"
