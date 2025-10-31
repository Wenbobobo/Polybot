from __future__ import annotations

from typing import Iterable, Dict, Any

from polybot.adapters.polymarket.orderbook import OrderbookAssembler


def apply_orderbook_events(market_id: str, events: Iterable[Dict[str, Any]]):
    ob = OrderbookAssembler(market_id)
    last = None
    for e in events:
        etype = e.get("type")
        if etype == "snapshot":
            last = ob.apply_snapshot(e)
        elif etype == "delta":
            last = ob.apply_delta(e)
    return last

