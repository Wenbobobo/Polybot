import asyncio
import json
from contextlib import asynccontextmanager

import pytest
import websockets

from polybot.adapters.polymarket.ws import OrderbookWSClient


@asynccontextmanager
async def ws_server(messages):
    async def handler(websocket):
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

