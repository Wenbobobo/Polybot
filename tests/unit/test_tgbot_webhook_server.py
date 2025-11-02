import httpx
from polybot.tgbot.webhook_server import start_tg_server, stop_tg_server
from polybot.tgbot.agent import BotAgent, BotContext
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def test_tgbot_webhook_accepts_and_authorizes():
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0))
    agent = BotAgent(engine, BotContext(market_id="m1", outcome_yes_id="yes"))
    server, _ = start_tg_server(agent, host="127.0.0.1", port=0, secret_path="/tg", allowed_ids=[123])
    port = server.server_address[1]
    try:
        with httpx.Client(trust_env=False, timeout=5.0) as client:
            # forbidden user
            r = client.post(f"http://127.0.0.1:{port}/tg", json={"message": {"from": {"id": 999}, "text": "/status"}})
            assert r.status_code == 403
            # allowed user
            r2 = client.post(f"http://127.0.0.1:{port}/tg", json={"message": {"from": {"id": 123}, "text": "/buy 0.4 1"}})
            assert r2.status_code == 200 and "ok: placed" in r2.text
    finally:
        stop_tg_server(server)

