from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translate_polymarket_snapshot_and_update():
    snap = {"type": "l2_snapshot", "seq": 10, "bids": [[0.4, 100.0]], "asks": [[0.6, 50.0]]}
    out = translate_polymarket_message(snap)
    assert out and out["type"] == "snapshot" and out["seq"] == 10

    upd = {"type": "l2_update", "seq": 11, "bids": [[0.41, 10.0]], "checksum": "abc"}
    out2 = translate_polymarket_message(upd)
    assert out2 and out2["type"] == "delta" and out2["checksum"] == "abc"

    passthrough = {"type": "snapshot", "seq": 1}
    assert translate_polymarket_message(passthrough) == passthrough

