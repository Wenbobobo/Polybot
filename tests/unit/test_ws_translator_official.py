from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.ingestion.validator import validate_message


def test_translator_handles_official_like_fields():
    msg = {
        "type": "l2_update",
        "seq": 12,
        "bids": [[0.42, 2.0]],
        "channel": "l2",
        "market": "mkt-1",
        "ts_ms": 1712345678000,
        "checksum": "abcd",
    }
    out = translate_polymarket_message(msg)
    assert out is not None
    ok, reason = validate_message(out)
    assert ok, reason
    assert out.get("market") == "mkt-1"
    assert out.get("checksum") == "abcd"


def test_translator_accepts_wrapped_data_payload():
    msg = {
        "type": "l2_snapshot",
        "data": {"seq": 1, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]},
        "channel": "l2",
        "market": "mkt-2",
    }
    out = translate_polymarket_message(msg)
    assert out and out["type"] == "snapshot" and out["seq"] == 1
    assert out.get("market") == "mkt-2"

