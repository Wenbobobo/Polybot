from __future__ import annotations

from typing import Dict


def orderbook_checksum(bids: Dict[float, float], asks: Dict[float, float]) -> str:
    # Simple deterministic checksum: counts + rounded sum(price*size) per side
    def agg(side: Dict[float, float]) -> float:
        total = 0.0
        for p, s in side.items():
            total += float(p) * float(s)
        # reduce float noise
        return round(total, 6)

    bcount = len(bids)
    acount = len(asks)
    bsum = agg(bids)
    asum = agg(asks)
    return f"b{bcount}a{acount}v{bsum+asum}"

