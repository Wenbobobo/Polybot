from polybot.adapters.polymarket.orderbook import OrderbookAssembler


def test_orderbook_assembler_snapshot_and_delta():
    ob = OrderbookAssembler(market_id="m1")
    snap = {
        "seq": 10,
        "bids": [[0.40, 100.0], [0.39, 50.0]],
        "asks": [[0.45, 80.0], [0.46, 40.0]],
    }
    book = ob.apply_snapshot(snap)
    assert book.seq == 10
    assert book.best_bid().price == 0.40
    assert book.best_ask().price == 0.45

    # Apply delta: add to best bid, remove lowest ask, and add a better ask
    delta = {
        "seq": 11,
        "bids": [[0.40, 20.0]],
        "asks": [[0.45, -80.0], [0.44, 10.0]],
    }
    book2 = ob.apply_delta(delta)
    assert book2.seq == 11
    assert book2.bids[0.40] == 120.0
    assert 0.45 not in book2.asks
    assert book2.best_ask().price == 0.44

