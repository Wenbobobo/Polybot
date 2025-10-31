from polybot.tgbot.commands import parse_command
from polybot.tgbot.agent import BotAgent, BotContext
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer


def test_parse_command_variants():
    assert parse_command("/BUY 0.5 1").cmd == "buy"
    assert parse_command("status").cmd == "status"


def test_agent_buy_executes():
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=None)
    agent = BotAgent(engine, BotContext(market_id="m1", outcome_yes_id="yes"))
    out = agent.handle_text("/buy 0.5 1")
    assert out.startswith("ok:")

