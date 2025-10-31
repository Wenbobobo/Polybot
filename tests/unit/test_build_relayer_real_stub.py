def test_build_relayer_real_with_injected_client(monkeypatch):
    from polybot.adapters.polymarket.relayer import build_relayer

    class Stub:
        def place_orders(self, orders):
            return []

        def cancel_orders(self, ids):
            return []

    r = build_relayer("real", client=Stub())
    assert hasattr(r, "place_orders")

