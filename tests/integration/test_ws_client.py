import asyncio
import json
from contextlib import asynccontextmanager

import pytest
import websockets

from polybot.adapters.polymarket.ws import OrderbookWSClient


@asynccontextmanager
async def ws_server(messages, expect_subscribe: dict | None = None):
    async def handler(websocket):
        if expect_subscribe is not None:
            raw = await websocket.recv()
            assert json.loads(raw) == expect_subscribe
        for m in messages:
            await websocket.send(json.dumps(m))
        await asyncio.sleep(0.05)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    try:
        yield f"ws://{host}:{port}"
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_ws_client_receives_messages():
    events = [
        {"type": "snapshot", "seq": 10, "bids": [[0.4, 100.0]], "asks": [[0.47, 50.0]]},
        {"type": "delta", "seq": 11, "bids": [[0.41, 20.0]]},
    ]
    async with ws_server(events) as url:
        async with OrderbookWSClient(url) as client:
            received = []
            async for m in client.messages():
                received.append(m.raw)
                if len(received) >= len(events):
                    break
    assert received == events


@pytest.mark.asyncio
async def test_ws_client_sends_subscribe_before_receiving():
    events = [{"type": "snapshot", "seq": 1, "bids": [], "asks": []}]
    subscribe = {"op": "subscribe", "channel": "orderbook", "market": "m1"}
    async with ws_server(events, expect_subscribe=subscribe) as url:
        async with OrderbookWSClient(url, subscribe_message=subscribe) as client:
            msgs = []
            async for m in client.messages():
                msgs.append(m.raw)
                break
    assert msgs and msgs[0]["type"] == "snapshot"
