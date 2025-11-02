from polybot.adapters.polymarket.relayer import RelayerClient, OrderRequest
from polybot.observability.metrics import get_counter_labelled, reset as metrics_reset


class FailingInner:
    def place_orders(self, payload):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")


def test_relayer_client_increments_place_errors_on_exception():
    metrics_reset()
    rc = RelayerClient(FailingInner())
    req = OrderRequest(market_id="m1", outcome_id="y", side="buy", price=0.4, size=1.0)
    try:
        rc.place_orders([req])
    except RuntimeError:
        pass
    assert get_counter_labelled("relayer_place_errors", {"market": "m1"}) == 1

