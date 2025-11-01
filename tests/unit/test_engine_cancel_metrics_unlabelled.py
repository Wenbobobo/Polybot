from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.observability.metrics import get_counter


def test_engine_cancel_increments_unlabelled_counters():
    eng = ExecutionEngine(FakeRelayer(fill_ratio=0.0))
    before_c = get_counter("relayer_cancel_count")
    before_ms = get_counter("relayer_cancel_ms_sum")
    eng.cancel_client_orders(["cid1", "cid2"])  # noop for FakeRelayer
    after_c = get_counter("relayer_cancel_count")
    after_ms = get_counter("relayer_cancel_ms_sum")
    assert after_c == before_c + 2
    assert after_ms >= before_ms

