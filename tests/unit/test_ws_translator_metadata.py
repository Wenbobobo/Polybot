from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translator_preserves_ts_ms_and_market():
    msg = {"type": "l2_update", "seq": 5, "bids": [], "channel": "l2", "market": "mkt-1", "ts_ms": 1712000000000}
    out = translate_polymarket_message(msg)
    assert out["type"] == "delta" and out["market"] == "mkt-1" and out["ts_ms"] == 1712000000000
    msg2 = {"type": "l2_snapshot", "data": {"seq": 1, "bids": [], "asks": []}, "channel": "l2", "ts_ms": 123}
    out2 = translate_polymarket_message(msg2)
    assert out2["type"] == "snapshot" and out2["ts_ms"] == 123

