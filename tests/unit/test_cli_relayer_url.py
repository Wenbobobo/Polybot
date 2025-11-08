import types

from polybot.cli import commands
from polybot.adapters.polymarket.relayer import OrderAck


class _StubRelayer:
    def __init__(self):
        self.placed = []

    def place_orders(self, reqs, idempotency_prefix=None):
        self.placed.extend(reqs)
        return [OrderAck(order_id="oid", accepted=True, status="accepted")]


def test_relayer_live_order_resolves_url(monkeypatch):
    stub = _StubRelayer()
    monkeypatch.setattr(commands, "build_relayer", lambda *a, **k: stub, raising=True)
    monkeypatch.setattr(commands, "_resolve_market_choice", lambda **kwargs: {"market_id": "mid", "selected_outcome_id": "oid"}, raising=True)
    cmd = commands.cmd_relayer_live_order(
        market_id="ignored",
        outcome_id="ignored",
        side="buy",
        price=0.3,
        size=1.0,
        base_url="https://clob",
        private_key="0x",
        confirm_live=True,
        url="https://polymarket.com/event/foo",
    )
    assert "live placed=1" in cmd
    assert stub.placed[0].market_id == "mid"


def test_relayer_live_order_config_passes_url(monkeypatch):
    class _Cfg(types.SimpleNamespace):
        pass

    cfg = _Cfg(
        relayer_base_url="https://clob",
        relayer_private_key="0x",
        relayer_chain_id=137,
        relayer_timeout_s=10.0,
        relayer_builder=None,
    )

    monkeypatch.setattr(commands, "load_service_config", lambda path: cfg, raising=True)
    called = {}

    def _mock_live(**kwargs):
        called["url"] = kwargs["url"]

    monkeypatch.setattr(commands, "cmd_relayer_live_order", lambda *a, **k: _mock_live(**k), raising=True)
    commands.cmd_relayer_live_order_from_config(
        "config/service.toml",
        "ignored",
        "ignored",
        "buy",
        0.3,
        1.0,
        confirm_live=True,
        url="https://polymarket.com/event/foo",
    )
    assert called["url"] == "https://polymarket.com/event/foo"
