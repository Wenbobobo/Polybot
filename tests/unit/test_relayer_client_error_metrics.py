import pytest

from polybot.adapters.polymarket.relayer import RelayerClient, OrderRequest
from polybot.observability.metrics import get_counter_labelled


class StubErr:
    def place_orders(self, orders):
        raise RuntimeError("boom")

    def cancel_orders(self, ids):
        return []


def test_relayer_client_increments_place_errors_on_exception():
    before = get_counter_labelled("relayer_place_errors", {"market": "m1"})
    rc = RelayerClient(StubErr())
    req = OrderRequest(market_id="m1", outcome_id="o", side="buy", price=0.4, size=1.0, client_order_id="cid")
    with pytest.raises(RuntimeError):
        rc.place_orders([req])
    after = get_counter_labelled("relayer_place_errors", {"market": "m1"})
    assert after == before + 1

