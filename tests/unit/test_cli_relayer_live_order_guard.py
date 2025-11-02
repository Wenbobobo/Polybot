from polybot.cli import commands as cmds


def test_live_order_requires_confirm(monkeypatch):
    out = cmds.cmd_relayer_live_order(
        "m1", "o1", "buy", 0.4, 1.0, base_url="u", private_key="0x" + "1" * 64, confirm_live=False
    )
    assert out.startswith("live order blocked")


def test_live_order_with_stub(monkeypatch):
    class StubRelayer:
        def place_orders(self, reqs, idempotency_prefix=None):
            from polybot.adapters.polymarket.relayer import OrderAck

            return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]

    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: StubRelayer())
    out = cmds.cmd_relayer_live_order(
        "m1", "o1", "buy", 0.4, 1.0, base_url="u", private_key="0x" + "1" * 64, confirm_live=True
    )
    assert out.startswith("live placed=1 accepted=1")

