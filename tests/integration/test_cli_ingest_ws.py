import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import websockets

from polybot.cli.commands import cmd_ingest_ws_async
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


def test_cli_cmd_ingest_ws(tmp_path: Path):
    events = [
        {"type": "snapshot", "seq": 10, "bids": [[0.4, 100.0]], "asks": [[0.47, 50.0]]},
        {"type": "delta", "seq": 11, "bids": [[0.41, 20.0]]},
    ]
    dbfile = tmp_path / "test.db"

    async def run():
        async with ws_server(events) as url:
            await cmd_ingest_ws_async(url, market_id="m1", db_url=f"sqlite:///{dbfile}", max_messages=2)

    asyncio.run(run())

    con = connect_sqlite(f"sqlite:///{dbfile}")
    cur = con.execute("SELECT COUNT(*) FROM orderbook_snapshots WHERE market_id='m1'")
    assert cur.fetchone()[0] == 1
    cur = con.execute("SELECT COUNT(*) FROM orderbook_events WHERE market_id='m1'")
    assert cur.fetchone()[0] == 1
