from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.exec.engine import ExecutionEngine


def test_fake_relayer_full_fill_and_engine_executes():
    relayer = FakeRelayer(fill_ratio=1.0)
    engine = ExecutionEngine(relayer)
    plan = ExecutionPlan(
        intents=[
            OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=10.0),
            OrderIntent(market_id="m1", outcome_id="o2", side="buy", price=0.6, size=10.0),
        ],
        expected_profit=0.0,
        rationale="test",
    )
    result = engine.execute_plan(plan)
    assert result.fully_filled is True
    assert len(result.acks) == 2
    assert all(a.accepted for a in result.acks)


def test_fake_relayer_partial_fill_marks_not_fully_filled():
    relayer = FakeRelayer(fill_ratio=0.5)
    engine = ExecutionEngine(relayer)
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=10.0)],
        expected_profit=0.0,
        rationale="test",
    )
    result = engine.execute_plan(plan)
    assert result.fully_filled is False
    assert result.acks[0].filled_size == 5.0
    assert result.acks[0].remaining_size == 5.0

