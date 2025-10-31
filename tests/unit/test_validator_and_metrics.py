from polybot.ingestion.validator import validate_message
from polybot.observability.metrics import get_counter, inc


def test_validate_message_accepts_snapshot_and_delta():
    ok, _ = validate_message({"type": "snapshot", "seq": 1, "bids": [], "asks": []})
    assert ok
    ok, _ = validate_message({"type": "delta", "seq": 2})
    assert ok
    ok, reason = validate_message({"type": "snapshot", "seq": -1})
    assert not ok and "validation_error" in reason


def test_metrics_counter_increments():
    base = get_counter("ingestion_msg_invalid")
    inc("ingestion_msg_invalid")
    assert get_counter("ingestion_msg_invalid") == base + 1

