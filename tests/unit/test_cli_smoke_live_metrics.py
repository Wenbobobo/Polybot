from pathlib import Path

from polybot.cli import commands as cmds


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):
        from polybot.adapters.polymarket.relayer import OrderAck
        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_smoke_live_appends_metrics(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "fake"

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        subscribe = false
        max_messages = 1
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: StubRelayer())
    out = cmds.cmd_smoke_live(str(cfg), "m1", "o", "buy", 0.4, 1.0, base_url="u", private_key="0x" + "1" * 64)
    assert "metrics: rate_limited=" in out and "builder_errors=" in out
