import asyncio

import types

from polybot.adapters.polymarket.ws import OrderbookWSClient


class FakeWS:
    def __init__(self, messages):
        self._messages = list(messages)
        self._closed = False

    def __aiter__(self):
        self._iter = iter(self._messages)
        return self

    async def __anext__(self):
        try:
            v = next(self._iter)
        except StopIteration:
            raise StopAsyncIteration
        # Allow raising an exception token to simulate connection error
        if isinstance(v, Exception):
            raise v
        return v

    async def send(self, data):  # noqa: D401
        return None

    async def close(self):  # noqa: D401
        self._closed = True


def test_ws_client_reconnects_and_resubscribes(monkeypatch):
    calls = {"n": 0}

    async def fake_connect(url, ping_interval=20.0):  # noqa: D401
        calls["n"] += 1
        # First connection: one message then error
        if calls["n"] == 1:
            return FakeWS(["{\"type\": \"l2_snapshot\", \"seq\": 1, \"bids\": [], \"asks\": []}", RuntimeError("boom")])
        # Second connection: one more message then end
        return FakeWS(["{\"type\": \"l2_update\", \"seq\": 2}"])

    import polybot.adapters.polymarket.ws as wsmod

    monkeypatch.setattr(wsmod.websockets, "connect", fake_connect)

    async def run_once():
        out = []
        async with OrderbookWSClient("ws://x", subscribe_message={"sub": 1}, max_reconnects=1, backoff_ms=0) as client:
            async for m in client.messages():
                out.append(m.raw)
                if len(out) >= 2:
                    break
        return out, calls["n"]

    out, n = asyncio.run(run_once())
    assert n == 2
    assert out[0]["type"] == "l2_snapshot" and out[1]["type"] == "l2_update"
