import json

from polybot.cli.commands import cmd_markets_resolve


class _NullHttpClient:
    def __init__(self, *args, **kwargs):
        pass

    def get_simplified_markets(self, cursor=None, limit=100):
        return {"data": [], "next_cursor": None}


def test_markets_resolve_uses_next_data_fallback(monkeypatch):
    # Disable py-clob path so the resolver falls back to HTTP/Next.js
    monkeypatch.setattr("polybot.cli.commands._make_pyclob_client", lambda **kwargs: None, raising=True)
    monkeypatch.setattr("polybot.cli.commands.ClobHttpClient", lambda *args, **kwargs: _NullHttpClient(), raising=True)

    next_payload = {
        "market_id": "0xnext123",
        "title": "First to 5k: Gold or ETH?",
        "outcomes": [
            {"outcome_id": "GOLD_TOKEN", "name": "Gold"},
            {"outcome_id": "ETH_TOKEN", "name": "ETH"},
        ],
        "selected_outcome_id": "ETH_TOKEN",
        "selected_outcome_name": "ETH",
    }

    monkeypatch.setattr(
        "polybot.cli.commands._resolve_market_via_next_data",
        lambda url, timeout_s: next_payload,
        raising=True,
    )

    out = cmd_markets_resolve(
        url="https://polymarket.com/event/first-to-5k-gold-or-eth?tid=1762222414610",
        prefer="yes",
        as_json=True,
        debug=True,
    )
    data = json.loads(out)
    assert data and data[0]["market_id"] == "0xnext123"
    assert data[0]["selected_outcome_id"] in {"GOLD_TOKEN", "ETH_TOKEN"}
