import asyncio
import json
from contextlib import asynccontextmanager

import websockets

from polybot.service.runner import ServiceRunner, MarketSpec
from polybot.observability.metrics import get_counter_labelled, reset as metrics_reset


@asynccontextmanager
async def ws_server(messages):
    async def handler(websocket):
        try:
            await websocket.recv()
        except Exception:
            pass
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


def test_service_runner_marks_done_metric(tmp_path):
    metrics_reset()
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
        {"type": "l2_update", "seq": 3, "bids": [[0.41, 10.0]]},
    ]

    async def run():
        async with ws_server(events) as url:
            sr = ServiceRunner(db_url=":memory:")
            specs = [MarketSpec(market_id="m_done", outcome_yes_id="yes", ws_url=url, max_messages=3)]
            await sr.run_markets(specs)

    asyncio.run(run())
    assert get_counter_labelled("service_market_done", {"market": "m_done"}) == 1

