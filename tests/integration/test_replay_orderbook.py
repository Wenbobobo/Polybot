from polybot.observability.replay import apply_orderbook_events


def test_apply_orderbook_events_snapshot_then_deltas():
    events = [
        {"type": "snapshot", "seq": 10, "bids": [[0.4, 100.0]], "asks": [[0.47, 50.0]]},
        {"type": "delta", "seq": 11, "bids": [[0.41, 20.0]]},
        {"type": "delta", "seq": 12, "asks": [[0.47, -50.0], [0.46, 40.0]]},
    ]
    book = apply_orderbook_events("m1", events)
    assert book is not None
    assert book.seq == 12
    assert book.best_bid().price == 0.41
    assert book.best_ask().price == 0.46

