import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import websockets

from polybot.cli.commands import cmd_quoter_run_ws_async
from polybot.storage.db import connect_sqlite


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


def test_cli_quoter_run_ws_places_orders(tmp_path: Path):
    # Polymarket-like messages
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
        {"type": "l2_update", "seq": 3, "bids": [[0.41, 10.0]]},
    ]
    dbfile = tmp_path / "test.db"

    async def run():
        async with ws_server(events) as url:
            await cmd_quoter_run_ws_async(url, market_id="m1", outcome_yes_id="yes", db_url=f"sqlite:///{dbfile}", max_messages=3)

    asyncio.run(run())

    con = connect_sqlite(f"sqlite:///{dbfile}")
    cnt = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert cnt >= 2

