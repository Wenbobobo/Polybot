from polybot.cli.commands import cmd_relayer_live_order_from_config


class _Cfg:
    def __init__(self):
        self.relayer_base_url = "https://clob.polymarket.com"
        self.relayer_private_key = "0x" + "1" * 64
        self.relayer_chain_id = 137
        self.relayer_timeout_s = 5.0


def test_relayer_live_order_config_blocks_without_confirm(monkeypatch):
    # Patch config loader to avoid reading files
    monkeypatch.setattr("polybot.cli.commands.load_service_config", lambda p: _Cfg())
    # Patch underlying live order to avoid network
    def _live(**kwargs):
        return "blocked"

    monkeypatch.setattr("polybot.cli.commands.cmd_relayer_live_order", lambda **kw: _live(**kw))
    out = cmd_relayer_live_order_from_config(
        "config/service.toml",
        market_id="m1",
        outcome_id="yes",
        side="buy",
        price=0.01,
        size=0.01,
        confirm_live=False,
        as_json=True,
    )
    assert "blocked" in out

