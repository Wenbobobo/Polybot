from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.ingestion.validator import validate_message


def test_translator_ignores_unknown_extra_fields():
    msg = {
        "type": "l2_snapshot",
        "channel": "l2",
        "market": "m1",
        "extra": {"foo": 1},
        "data": {"seq": 1, "bids": [[0.4, 1.0], [0.3, 2.0]], "asks": [[0.6, 1.0]], "weird": [1, 2, 3]},
    }
    out = translate_polymarket_message(msg)
    assert out is not None and out.get("type") == "snapshot"
    ok, reason = validate_message(out)
    assert ok, reason

