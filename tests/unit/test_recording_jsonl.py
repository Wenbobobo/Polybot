from pathlib import Path

from polybot.observability.recording import write_jsonl, read_jsonl


def test_write_and_read_jsonl(tmp_path: Path):
    events = [
        {"type": "snapshot", "market_id": "m1", "seq": 10},
        {"type": "delta", "market_id": "m1", "seq": 11, "bids": [[0.4, 10.0]]},
    ]
    file = tmp_path / "rec" / "m1.jsonl"
    write_jsonl(file, events)
    out = list(read_jsonl(file))
    assert out == events

