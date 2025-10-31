from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional


TimeInForce = Literal["IOC", "FOK", "GTC"]


@dataclass
class OrderRequest:
    market_id: str
    outcome_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    tif: TimeInForce = "IOC"
    client_order_id: Optional[str] = None


@dataclass
class OrderAck:
    order_id: str
    accepted: bool
    filled_size: float = 0.0
    remaining_size: float = 0.0
    status: Literal["accepted", "rejected", "filled", "partial"] = "accepted"


class FakeRelayer:
    """A deterministic fake relayer for tests/integration without network.

    Rules:
    - Accepts all orders with price in [0,1] and size>0
    - Can be configured with a fill_ratio to simulate partial fills
    """

    def __init__(self, fill_ratio: float = 1.0):
        self.fill_ratio = max(0.0, min(1.0, fill_ratio))
        self._seq = 0

    def place_orders(self, reqs: List[OrderRequest]) -> List[OrderAck]:
        acks: List[OrderAck] = []
        for r in reqs:
            self._seq += 1
            if not (0.0 <= r.price <= 1.0) or r.size <= 0:
                acks.append(OrderAck(order_id=f"ord-{self._seq}", accepted=False, status="rejected"))
                continue
            filled = round(r.size * self.fill_ratio, 10)
            remaining = max(0.0, r.size - filled)
            status = "filled" if remaining == 0.0 else ("partial" if filled > 0.0 else "accepted")
            acks.append(
                OrderAck(
                    order_id=f"ord-{self._seq}",
                    accepted=True,
                    filled_size=filled,
                    remaining_size=remaining,
                    status=status,
                )
            )
        return acks

