import asyncio
import json
from contextlib import asynccontextmanager

import websockets

from polybot.cli import commands as cmds


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


def test_service_calls_status_summary_on_completion(tmp_path):
    called = {"v": 0}

    def fake_summary(db_url: str = ":memory:") -> str:  # type: ignore[no-redef]
        called["v"] += 1
        return "ok"

    async def run():
        async with ws_server([
            {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
            {"type": "l2_update", "seq": 2},
        ]) as url:
            cfg = tmp_path / "svc.toml"
            cfg.write_text(
                f"""
                [service]
                db_url = ":memory:"

                [[market]]
                market_id = "m1"
                outcome_yes_id = "yes"
                ws_url = "{url}"
                subscribe = true
                max_messages = 2
                """
            )
            # Monkeypatch only within this scope
            orig = cmds.cmd_status_summary
            cmds.cmd_status_summary = fake_summary  # type: ignore[assignment]
            try:
                await cmds.cmd_run_service_from_config_async(str(cfg))
            finally:
                cmds.cmd_status_summary = orig  # type: ignore[assignment]

    asyncio.run(run())
    assert called["v"] == 1

