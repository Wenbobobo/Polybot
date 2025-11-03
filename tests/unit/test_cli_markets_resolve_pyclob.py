import json

from polybot.cli.commands import cmd_markets_resolve


class _StubPyClob:
    def get_simplified_markets(self, cursor=None):
        return {
            "data": [
                {"question": "Will Coinbase list HYPE in 2025?", "condition_id": "cond-1"},
            ],
            "next_cursor": "LTE=",
        }

    def get_market(self, condition_id):
        return {
            "question": "Will Coinbase list HYPE in 2025?",
            "tokens": [
                {"name": "Yes", "token_id": "YES_TOKEN"},
                {"name": "No", "token_id": "NO_TOKEN"},
            ],
        }


def test_cli_markets_resolve_with_url_and_pyclob(monkeypatch):
    # Patch py-clob client builder
    monkeypatch.setattr("polybot.cli.commands._make_pyclob_client", lambda **kwargs: _StubPyClob(), raising=True)
    out = cmd_markets_resolve(
        url="https://polymarket.com/event/will-coinbase-list-hype-in-2025/will-coinbase-list-hype-in-2025?tid=1762100517211",
        prefer="yes",
        as_json=True,
    )
    data = json.loads(out)
    assert data and data[0]["market_id"] == "cond-1"
    assert data[0]["selected_outcome_id"] == "YES_TOKEN"
