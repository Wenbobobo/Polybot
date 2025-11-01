import asyncio

from polybot.adapters.polymarket.ws import OrderbookWSClient


class PingWS:
    def __init__(self, messages):
        self._msgs = messages
        self.pings = 0

    def __aiter__(self):
        self._it = iter(self._msgs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, data):
        return None

    async def close(self):
        return None

    async def ping(self):
        self.pings += 1


def test_ws_client_ping_task(monkeypatch):
    import polybot.adapters.polymarket.ws as wsmod

    # monkeypatch connect to return a ws with ping counting
    ws = PingWS(["{\"type\": \"l2_snapshot\", \"seq\": 1, \"bids\": [], \"asks\": []}"])

    async def fake_connect(url, ping_interval=20.0):
        return ws

    monkeypatch.setattr(wsmod.websockets, "connect", fake_connect)

    async def run_once():
        async with OrderbookWSClient("ws://x", subscribe_message={"sub": 1}, enable_ping_task=True, ping_every_ms=1) as client:
            async for m in client.messages():
                # wait a little to let ping run
                await asyncio.sleep(0.05)
                break
        return ws.pings

    pings = asyncio.run(run_once())
    assert pings >= 1
