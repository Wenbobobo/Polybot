from polybot.cli import commands as cmds


def test_cli_relayer_dry_run_forwards_chain_and_timeout(monkeypatch):
    seen = {}

    def fake_build(kind, **kw):
        nonlocal seen
        seen = kw
        class R:
            def place_orders(self, reqs, idempotency_prefix=None):
                from polybot.adapters.polymarket.relayer import OrderAck
                return [OrderAck(order_id="o1", accepted=True)]
        return R()

    monkeypatch.setattr(cmds, "build_relayer", fake_build)
    out = cmds.cmd_relayer_dry_run("m1", "o1", "buy", 0.3, 1.0, base_url="u", private_key="k", chain_id=99, timeout_s=5.0)
    assert out.startswith("placed=1")
    assert seen.get("chain_id") == 99 and seen.get("timeout_s") == 5.0

