import pytest

from polybot.adapters.polymarket.relayer import RetryRelayer, OrderRequest
from polybot.observability.metrics import get_counter, get_counter_labelled, reset as metrics_reset


class BuilderFailingInner:
    def place_orders(self, reqs, idempotency_prefix=None):  # type: ignore[no-untyped-def]
        err = Exception("BUILDER_AUTH_UNAVAILABLE: credentials missing")
        setattr(err, "code", "BUILDER_AUTH_UNAVAILABLE")
        raise err


def test_retry_relayer_increments_builder_error_metrics():
    metrics_reset()
    inner = BuilderFailingInner()
    rr = RetryRelayer(inner, max_retries=0)
    reqs = [OrderRequest(market_id="m1", outcome_id="o1", side="buy", price=0.4, size=1.0)]
    with pytest.raises(Exception):
        rr.place_orders(reqs, idempotency_prefix="plan")
    assert get_counter("relayer_builder_errors_total") == 1
    assert get_counter_labelled("relayer_builder_errors", {"market": "m1"}) == 1
