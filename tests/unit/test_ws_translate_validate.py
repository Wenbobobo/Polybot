import json
from pathlib import Path

from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.ingestion.validator import validate_message


def test_translate_and_validate_polymarket_messages():
    msgs = json.loads(Path("tests/fixtures/ws_polymarket_messages.json").read_text(encoding="utf-8"))
    out = []
    for m in msgs:
        t = translate_polymarket_message(m)
        assert t is not None
        ok, reason = validate_message(t)
        assert ok, reason
        out.append(t)
    assert out[0]["type"] == "snapshot" and out[1]["type"] == "delta"

