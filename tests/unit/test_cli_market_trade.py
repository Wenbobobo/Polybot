import json
from types import SimpleNamespace

from polybot.cli import commands as cmds


def _fake_cfg():
    return SimpleNamespace(
        relayer_base_url="https://clob.polymarket.com",
        relayer_chain_id=137,
        relayer_timeout_s=10.0,
        relayer_type="real",
        relayer_private_key="0x" + "1" * 64,
    )


def test_market_trade_info_only(monkeypatch):
    monkeypatch.setattr(cmds, "load_service_config", lambda path: _fake_cfg())
    monkeypatch.setattr(
        cmds,
        "_resolve_market_choice",
        lambda **kwargs: {
            "market_id": "m1",
            "selected_outcome_id": "o1",
            "selected_outcome_name": "Yes",
            "title": "Sample Market",
        },
    )
    monkeypatch.setattr(
        cmds,
        "_fetch_market_overview",
        lambda *args, **kwargs: {
            "market": {"market_id": "m1", "outcome_id": "o1", "title": "Sample Market", "outcome_name": "Yes"},
            "prices": {"buy": {"price": "0.40"}, "sell": {"price": "0.60"}, "midpoint": {"midpoint": "0.50"}, "spread": {"spread": "0.20"}},
        },
    )
    out = cmds.cmd_market_trade(
        config_path="config/service.toml",
        url="https://polymarket.com/event/foo",
        side="buy",
        price=0.4,
        size=1.0,
        confirm_live=False,
        as_json=True,
    )
    data = json.loads(out)
    assert data["market"]["market_id"] == "m1"
    assert "note" in data and "Add --confirm-live" in data["note"]
    assert "entry" not in data


def test_market_trade_executes_entry_and_close(monkeypatch):
    monkeypatch.setattr(cmds, "load_service_config", lambda path: _fake_cfg())
    monkeypatch.setattr(
        cmds,
        "_resolve_market_choice",
        lambda **kwargs: {
            "market_id": "m2",
            "selected_outcome_id": "o2",
            "selected_outcome_name": "No",
            "title": "Another Market",
        },
    )
    monkeypatch.setattr(
        cmds,
        "_fetch_market_overview",
        lambda *args, **kwargs: {
            "market": {"market_id": "m2", "outcome_id": "o2", "title": "Another Market", "outcome_name": "No"},
            "prices": {"buy": {"price": "0.30"}, "sell": {"price": "0.70"}},
        },
    )
    calls = []

    def _fake_live_order(config_path, market_id, outcome_id, side, price, size, *, confirm_live=False, as_json=False, url=None, prefer=None, suppress_output=False, **_):
        calls.append((side, price, size, confirm_live, suppress_output, as_json))
        body = {"side": side, "price": price, "size": size}
        return json.dumps(body) if as_json else f"{side} {price} {size}"

    monkeypatch.setattr(cmds, "cmd_relayer_live_order_from_config", _fake_live_order)
    out = cmds.cmd_market_trade(
        config_path="config/service.toml",
        url="https://polymarket.com/event/bar",
        side="buy",
        price=0.35,
        size=2.0,
        close=True,
        close_price=0.45,
        close_size=1.5,
        confirm_live=True,
        as_json=True,
    )
    data = json.loads(out)
    assert data["entry"]["side"] == "buy"
    assert data["close"]["side"] == "sell"
    assert calls == [
        ("buy", 0.35, 2.0, True, True, True),
        ("sell", 0.45, 1.5, True, True, True),
    ]
