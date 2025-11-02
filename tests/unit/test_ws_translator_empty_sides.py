from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translator_accepts_empty_sides_snapshot():
    msg = {"type": "l2_snapshot", "seq": 1, "bids": [], "asks": []}
    out = translate_polymarket_message(msg)
    assert out and out["type"] == "snapshot" and out.get("bids") == [] and out.get("asks") == []


def test_translator_accepts_missing_sides_update():
    msg = {"type": "l2_update", "seq": 2}
    out = translate_polymarket_message(msg)
    assert out and out["type"] == "delta" and out.get("bids") == [] or out.get("bids") is None

