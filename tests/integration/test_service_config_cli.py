import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import websockets


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


def test_run_service_from_config(tmp_path: Path):
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
        {"type": "l2_update", "seq": 3, "bids": [[0.41, 10.0]]},
    ]

    async def run():
        async with ws_server(events) as url:
            cfg = tmp_path / "markets.toml"
            db_url = f"sqlite:///{(tmp_path/'test.db').as_posix()}"
            cfg.write_text(
                f"""
                [service]
                db_url = "{db_url}"

                [[market]]
                market_id = "m1"
                outcome_yes_id = "yes"
                ws_url = "{url}"
                subscribe = true
                max_messages = 3
                """
            )
            # Run via async command function
            from polybot.cli.commands import cmd_run_service_from_config_async
            await cmd_run_service_from_config_async(str(cfg))

    asyncio.run(run())
    dbfile = tmp_path / "test.db"
    assert dbfile.exists()
