import asyncio
import json
from contextlib import asynccontextmanager

import websockets

from polybot.cli.commands import cmd_quoter_run_ws_async


@asynccontextmanager
async def ws_server_with_subscribe(expected_sub):
    async def handler(websocket):
        raw = await websocket.recv()
        assert json.loads(raw) == expected_sub
        await websocket.send(json.dumps({"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]}))
        await websocket.send(json.dumps({"type": "l2_update", "seq": 2}))
        await asyncio.sleep(0.05)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    try:
        yield f"ws://{host}:{port}"
    finally:
        server.close()
        await server.wait_closed()


def test_quoter_run_ws_sends_subscribe():
    expected = {"op": "subscribe", "channel": "l2", "market": "m1"}

    async def run():
        async with ws_server_with_subscribe(expected) as url:
            await cmd_quoter_run_ws_async(url, market_id="m1", outcome_yes_id="yes", db_url=":memory:", max_messages=2, subscribe=True)

    asyncio.run(run())

