from __future__ import annotations

from typing import Dict, Any


def build_subscribe_l2(market_id: str) -> Dict[str, Any]:
    return {"op": "subscribe", "channel": "l2", "market": market_id}

