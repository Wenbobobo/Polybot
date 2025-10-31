from polybot.tgbot.agent import BotAgent, BotContext
from polybot.tgbot.runner import TelegramUpdateRunner
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def test_tg_runner_handles_update():
    agent = BotAgent(ExecutionEngine(FakeRelayer(fill_ratio=0.0)), BotContext(market_id="m1", outcome_yes_id="yes"))
    runner = TelegramUpdateRunner(agent)
    out = runner.handle_update({"message": {"text": "/help"}})
    assert "commands" in out

