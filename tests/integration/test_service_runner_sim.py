import asyncio
import json
from contextlib import asynccontextmanager

import websockets

from polybot.service.runner import ServiceRunner, MarketSpec
from polybot.storage.db import connect_sqlite


@asynccontextmanager
async def ws_server(messages):
    async def handler(websocket):
        # read optional subscribe
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=0.05)
            # ignore content
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


def test_service_runner_two_markets(tmp_path):
    events1 = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
        {"type": "l2_update", "seq": 3, "bids": [[0.41, 10.0]]},
    ]
    events2 = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.30, 200.0]], "asks": [[0.50, 200.0]]},
        {"type": "l2_update", "seq": 2},
        {"type": "l2_update", "seq": 3, "asks": [[0.49, 10.0]]},
    ]

    async def run():
        async with ws_server(events1) as url1, ws_server(events2) as url2:
            dbfile = tmp_path / "test.db"
            sr = ServiceRunner(db_url=f"sqlite:///{dbfile}")
            specs = [
                MarketSpec(market_id="m1", outcome_yes_id="yes", ws_url=url1, max_messages=3),
                MarketSpec(market_id="m2", outcome_yes_id="yes", ws_url=url2, max_messages=3),
            ]
            await sr.run_markets(specs)

    asyncio.run(run())
    con = connect_sqlite(f"sqlite:///{tmp_path/'test.db'}")
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt >= 4

