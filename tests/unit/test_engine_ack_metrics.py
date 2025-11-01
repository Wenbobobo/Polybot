from polybot.exec.engine import ExecutionEngine
from polybot.exec.planning import ExecutionPlan, OrderIntent
from polybot.adapters.polymarket.relayer import OrderAck
from polybot.observability.metrics import get_counter_labelled


class StubRelayer:
    def __init__(self, accepted=True):
        self.accepted = accepted

    def place_orders(self, reqs, idempotency_prefix=None):
        status = "accepted" if self.accepted else "rejected"
        return [OrderAck(order_id="o1", accepted=self.accepted, filled_size=0.0, remaining_size=reqs[0].size, status=status)]


def test_engine_ack_metrics_increment_for_accept_and_reject():
    plan = ExecutionPlan(intents=[OrderIntent(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)], expected_profit=0, rationale="r")

    # Accepted
    eng_ok = ExecutionEngine(StubRelayer(True))
    eng_ok.execute_plan(plan)
    assert get_counter_labelled("relayer_acks", {"market": "m1", "status": "accepted"}) >= 1
    assert get_counter_labelled("relayer_acks_accepted", {"market": "m1"}) >= 1

    # Rejected
    eng_bad = ExecutionEngine(StubRelayer(False))
    eng_bad.execute_plan(plan)
    assert get_counter_labelled("relayer_acks", {"market": "m1", "status": "rejected"}) >= 1
    assert get_counter_labelled("relayer_acks_rejected", {"market": "m1"}) >= 1

