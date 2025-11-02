from polybot.adapters.polymarket.relayer import RelayerClient
from polybot.observability.metrics import get_counter, reset as metrics_reset


class InnerFailCancel:
    def cancel_orders(self, client_oids):  # type: ignore[no-untyped-def]
        raise RuntimeError("fail")


def test_relayer_client_cancel_errors_metric_incremented_on_exception():
    metrics_reset()
    rc = RelayerClient(InnerFailCancel())
    try:
        rc.cancel_client_orders(["c1"])
    except RuntimeError:
        pass
    assert get_counter("relayer_cancel_errors_total") == 1

