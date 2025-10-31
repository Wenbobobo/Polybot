from polybot.cli.commands import cmd_relayer_dry_run


def test_relayer_dry_run_with_stub(monkeypatch):
    # Stub build_relayer to return a relayer with place_orders compliant to engine
    class StubRelayer:
        def place_orders(self, reqs, idempotency_prefix=None):
            from polybot.adapters.polymarket.relayer import OrderAck
            return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted", client_order_id=reqs[0].client_order_id)]

    from polybot.cli import commands as cmds

    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: StubRelayer())
    out = cmd_relayer_dry_run("m1", "o1", "buy", 0.4, 1.0, base_url="u", private_key="k")
    assert out.startswith("placed=1")

