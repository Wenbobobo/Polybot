from polybot.adapters.polymarket.ws_translator import translate_polymarket_message


def test_translator_prefers_top_level_metadata_over_wrapped():
    msg = {
        "type": "l2_update",
        "channel": "l2",  # top-level channel should be used
        "market": "m_top",
        "data": {
            "type": "l2_update",
            "seq": 5,
            "bids": [[0.42, 1.0]],
            "channel": "trades",
            "market": "m_inner",
        },
    }
    out = translate_polymarket_message(msg)
    assert out is not None
    assert out.get("market") == "m_top"
    assert out.get("channel") == "l2"

