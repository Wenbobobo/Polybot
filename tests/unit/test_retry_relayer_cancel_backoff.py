from polybot.adapters.polymarket.relayer import RetryRelayer, CancelAck


class AlwaysFailCancel:
    def __init__(self):
        self.calls = 0

    def cancel_client_orders(self, client_oids):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise RuntimeError("fail")


def test_retry_relayer_cancel_uses_sleeper_with_backoff():
    inner = AlwaysFailCancel()
    seen = []

    def sleeper(ms: int):
        seen.append(ms)

    rr = RetryRelayer(inner, max_retries=2, retry_sleep_ms=123, sleeper=sleeper)
    try:
        rr.cancel_client_orders(["c-1"])  # will raise after retries
    except RuntimeError:
        pass
    # sleeper called exactly max_retries times with the configured ms
    assert seen == [123, 123]
    assert inner.calls == 3  # initial + 2 retries

