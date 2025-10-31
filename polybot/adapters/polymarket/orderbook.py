from __future__ import annotations

from typing import Dict, Optional
from polybot.core.models import OrderBook, Level


class OrderbookAssembler:
    """Assembles an orderbook from snapshot and deltas.

    Snapshot format: {seq:int, bids:[[price,size],...], asks:[[price,size],...]}
    Delta format: {seq:int, bids:[[price,size_delta],...], asks:[[price,size_delta],...]}
    size_delta: set to 0 or negative to remove/decrease; positive to add/increase.
    Prices are floats (tick compliance validated elsewhere).
    """

    def __init__(self, market_id: str):
        self.market_id = market_id
        self._bids: Dict[float, float] = {}
        self._asks: Dict[float, float] = {}
        self._seq: int = 0

    def apply_snapshot(self, snapshot: dict) -> OrderBook:
        self._seq = int(snapshot.get("seq", 0))
        self._bids.clear()
        self._asks.clear()
        for p, s in snapshot.get("bids", []) or []:
            if s > 0:
                self._bids[float(p)] = float(s)
        for p, s in snapshot.get("asks", []) or []:
            if s > 0:
                self._asks[float(p)] = float(s)
        return OrderBook(self.market_id, self._seq, dict(self._bids), dict(self._asks))

    def apply_delta(self, delta: dict) -> OrderBook:
        next_seq = int(delta.get("seq", self._seq))
        if next_seq <= self._seq:
            # ignore old or duplicate deltas; caller handles resync policy
            return OrderBook(self.market_id, self._seq, dict(self._bids), dict(self._asks))

        for p, ds in delta.get("bids", []) or []:
            price = float(p)
            size = float(ds)
            new = max(0.0, self._bids.get(price, 0.0) + size)
            if new == 0.0:
                self._bids.pop(price, None)
            else:
                self._bids[price] = new
        for p, ds in delta.get("asks", []) or []:
            price = float(p)
            size = float(ds)
            new = max(0.0, self._asks.get(price, 0.0) + size)
            if new == 0.0:
                self._asks.pop(price, None)
            else:
                self._asks[price] = new

        self._seq = next_seq
        return OrderBook(self.market_id, self._seq, dict(self._bids), dict(self._asks))

    def best_bid(self) -> Optional[Level]:
        return OrderBook(self.market_id, self._seq, self._bids, self._asks).best_bid()

    def best_ask(self) -> Optional[Level]:
        return OrderBook(self.market_id, self._seq, self._bids, self._asks).best_ask()

