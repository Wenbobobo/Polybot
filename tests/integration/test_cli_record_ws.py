import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import websockets

from polybot.cli.commands import cmd_record_ws_async


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


def test_record_ws_writes_jsonl(tmp_path: Path):
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.4, 100.0]], "asks": [[0.6, 50.0]]},
        {"type": "l2_update", "seq": 2, "bids": [[0.41, 10.0]]},
    ]
    outfile = tmp_path / "out.jsonl"

    async def run():
        async with ws_server(events) as url:
            await cmd_record_ws_async(url, str(outfile), max_messages=2, subscribe=True, translate=True)

    asyncio.run(run())
    content = outfile.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 2
    # Lines should be translated to internal snapshot/delta
    import json as _json

    first = _json.loads(content[0])
    assert first.get("type") == "snapshot"

