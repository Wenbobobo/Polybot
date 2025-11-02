from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translator_handles_large_snapshot_with_metadata():
    bids = [[0.40 + i * 0.0001, 1.0] for i in range(1000)]
    asks = [[0.60 + i * 0.0001, 1.0] for i in range(1000)]
    msg = {"type": "l2_snapshot", "seq": 1, "bids": bids, "asks": asks, "channel": "l2", "market": "m1", "ts_ms": 123456789}
    out = translate_polymarket_message(msg)
    assert out and out["type"] == "snapshot" and out.get("market") == "m1" and out.get("channel") == "l2" and out.get("ts_ms") == 123456789


def test_translator_accepts_stringified_sizes_and_prices():
    msg = {"type": "l2_update", "seq": 2, "bids": [["0.41", "1.0"]], "channel": "l2"}
    out = translate_polymarket_message(msg)
    assert out and out["type"] == "delta" and out.get("bids") == [["0.41", "1.0"]]

