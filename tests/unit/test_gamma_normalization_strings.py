from polybot.adapters.polymarket.gamma import GammaClient


def test_normalize_markets_handles_string_outcome_ids():
    raw = [
        {
            "id": "m123",
            "title": "Market",
            "status": "active",
            "outcomes": ["0xabc", "0xdef"],
        }
    ]
    out = GammaClient.normalize_markets(raw)
    assert out and out[0]["market_id"] == "m123"
    oids = [o["outcome_id"] for o in out[0]["outcomes"]]
    assert oids == ["0xabc", "0xdef"]

