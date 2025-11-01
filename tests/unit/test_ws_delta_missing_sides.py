from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.ingestion.validator import validate_message


def test_ws_delta_missing_bids_asks_is_valid():
    msg = {"type": "l2_update", "channel": "l2", "seq": 10}
    out = translate_polymarket_message(msg)
    assert out is not None and out["type"] == "delta"
    ok, reason = validate_message(out)
    assert ok, reason

