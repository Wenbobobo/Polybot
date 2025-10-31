from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translator_ignores_non_l2_channels():
    msg = {"type": "l2_update", "seq": 1, "channel": "trades", "bids": [[0.5, 1.0]]}
    assert translate_polymarket_message(msg) is None
    msg2 = {"type": "l2_snapshot", "seq": 0, "channel": "l2", "bids": [], "asks": []}
    assert translate_polymarket_message(msg2)["type"] == "snapshot"

