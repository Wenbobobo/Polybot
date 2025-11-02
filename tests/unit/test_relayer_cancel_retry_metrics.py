from polybot.adapters.polymarket.relayer import RetryRelayer, CancelAck
from polybot.exec.engine import ExecutionEngine
from polybot.observability.metrics import get_counter, reset as metrics_reset


class FlakyCancelInner:
    def __init__(self):
        self.calls = 0

    def cancel_client_orders(self, client_oids):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("cancel failed")
        return [CancelAck(client_order_id=client_oids[0], canceled=True)]


def test_retry_relayer_cancel_retries_and_engine_metrics():
    metrics_reset()
    inner = FlakyCancelInner()
    rr = RetryRelayer(inner, max_retries=1, retry_sleep_ms=0, sleeper=lambda ms: None)
    eng = ExecutionEngine(rr)
    eng.cancel_client_orders(["c-1"])  # succeeds after retry
    # global retry counter incremented
    assert get_counter("relayer_retries_total") >= 1
    # engine cancel counters incremented
    assert get_counter("relayer_cancel_count") == 1
    assert get_counter("relayer_cancel_ms_sum") >= 0

