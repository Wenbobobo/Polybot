from polybot.adapters.polymarket.orderbook import OrderbookAssembler


def test_large_snapshot_and_delta_apply():
    ob = OrderbookAssembler(market_id="m1")
    bids = [[0.10 + i * 0.0001, 1.0] for i in range(1000)]
    asks = [[0.60 + i * 0.0001, 1.0] for i in range(1000)]
    snap = {"seq": 1, "bids": bids, "asks": asks}
    book = ob.apply_snapshot(snap)
    assert round(book.best_bid().price, 4) == round(bids[-1][0], 4)
    assert round(book.best_ask().price, 4) == round(asks[0][0], 4)
    # Apply a delta that improves best bid and removes a level from asks
    delta = {"seq": 2, "bids": [[bids[-1][0] + 0.001, 1.0]], "asks": [[asks[0][0], -1.0]]}
    b2 = ob.apply_delta(delta)
    assert b2.seq == 2
    assert b2.best_bid().price > book.best_bid().price
    assert b2.best_ask().price >= asks[1][0]

