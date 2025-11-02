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
        await asyncio.sleep(0.02)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    try:
        yield f"ws://{host}:{port}"
    finally:
        server.close()
        await server.wait_closed()


def test_service_runner_marks_runtime_ms(tmp_path):
    metrics_reset()
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
    ]

    async def run():
        async with ws_server(events) as url:
            sr = ServiceRunner(db_url=":memory:")
            specs = [MarketSpec(market_id="m_rt", outcome_yes_id="yes", ws_url=url, max_messages=2)]
            await sr.run_markets(specs)

    asyncio.run(run())
    assert get_counter_labelled("service_market_runtime_ms_sum", {"market": "m_rt"}) >= 0
    assert get_counter_labelled("service_market_runtime_count", {"market": "m_rt"}) == 1

