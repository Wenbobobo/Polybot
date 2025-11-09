from pathlib import Path

from polybot.cli import commands as cmds


class StubRelayer:
    def place_orders(self, reqs, idempotency_prefix=None):
        from polybot.adapters.polymarket.relayer import OrderAck

        return [OrderAck(order_id="o1", accepted=True, filled_size=0.0, remaining_size=reqs[0].size, status="accepted")]


def test_cli_smoke_live_runs_preflight_then_dry_run(monkeypatch, tmp_path: Path):
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
    assert "OK: preflight passed" in out
    assert "placed=1" in out


def test_cli_smoke_live_reports_builder_and_allowances(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        private_key = "0x1111111111111111111111111111111111111111111111111111111111111111"
        chain_id = 137
        timeout_s = 10.0

        [relayer.builder]
        mode = "local"
        api_key = "k"
        api_secret = "s"
        api_passphrase = "p"

        [[market]]
        market_id = "m1"
        outcome_yes_id = "yes"
        ws_url = "ws://127.0.0.1:1"
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr(cmds, "_builder_health_status", lambda cfg: (True, {"builder_type": "local", "address": "0xabc", "can_builder_auth": True, "source": "local"}, None, {}))
    monkeypatch.setattr(cmds, "_collect_allowances_for_smoke", lambda *a, **k: (None, {"usdc": {"allowance": "5"}, "outcome_error": "not set"}))
    monkeypatch.setattr(cmds, "cmd_relayer_dry_run", lambda *a, **k: "dry-run ok")
    out = cmds.cmd_smoke_live(str(cfg), "m1", "0xout", "buy", 0.4, 1.0, base_url="", private_key="")
    assert "builder:" in out and "allowances:" in out
