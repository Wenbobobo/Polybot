import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import websockets

from polybot.cli.commands import cmd_run_service_from_config_async
from polybot.storage.db import connect_sqlite


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


def test_service_config_spread_params_applied(tmp_path: Path):
    events = [
        {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
        {"type": "l2_update", "seq": 2},
    ]

    async def run():
        async with ws_server(events) as url:
            cfg = tmp_path / "markets.toml"
            db_url = f"sqlite:///{(tmp_path/'test.db').as_posix()}"
            cfg.write_text(
                f"""
                [service]
                db_url = "{db_url}"
                [service.spread]
                size = 2.5

                [[market]]
                market_id = "m1"
                outcome_yes_id = "yes"
                ws_url = "{url}"
                subscribe = true
                max_messages = 2
                """
            )
            await cmd_run_service_from_config_async(str(cfg))

    asyncio.run(run())
    con = connect_sqlite(f"sqlite:///{tmp_path/'test.db'}")
    row = con.execute("SELECT intents_json FROM exec_audit ORDER BY id DESC LIMIT 1").fetchone()
    import json as _json
    intents = _json.loads(row[0])
    sizes = {i["side"]: i["size"] for i in intents}
    assert sizes["buy"] == 2.5 and sizes["sell"] == 2.5

