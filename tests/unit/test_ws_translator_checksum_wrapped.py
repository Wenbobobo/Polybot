from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.ingestion.validator import validate_message


def test_translator_pulls_checksum_from_wrapped_data():
    msg = {
        "type": "l2_update",
        "channel": "l2",
        "data": {"seq": 5, "bids": [[0.5, 1.0]], "checksum": "cafe"},
        "market": "m1",
    }
    out = translate_polymarket_message(msg)
    assert out is not None
    ok, reason = validate_message(out)
    assert ok, reason
    assert out.get("checksum") == "cafe"

