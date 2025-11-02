from polybot.adapters.polymarket.gamma import GammaClient


def test_normalize_markets_handles_outcomes_json_string():
    raw = [
        {
            "id": "m456",
            "title": "Market",
            "status": "active",
            "outcomes": '["YES_TOKEN","NO_TOKEN"]',
        }
    ]
    out = GammaClient.normalize_markets(raw)
    oids = [o["outcome_id"] for o in out[0]["outcomes"]]
    assert oids == ["YES_TOKEN", "NO_TOKEN"]

