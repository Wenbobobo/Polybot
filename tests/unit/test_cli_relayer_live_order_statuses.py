from polybot.cli import commands as cmds


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):
        from polybot.adapters.polymarket.relayer import OrderAck

        return [
            OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="partial"),
            OrderAck(order_id="o2", accepted=False, filled_size=0.0, remaining_size=reqs[0].size, status="rejected"),
        ]


def test_relayer_live_order_prints_status_breakdown(monkeypatch):
    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: StubRelayer())
    out = cmds.cmd_relayer_live_order(
        "m1", "o1", "buy", 0.4, 1.0, base_url="u", private_key="0x" + "1" * 64, confirm_live=True
    )
    assert out.startswith("live placed=2 accepted=1")
    assert "partial=1" in out and "rejected=1" in out

