from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class OrderIntent:
    market_id: str
    outcome_id: str
    side: str  # 'buy' or 'sell'
    price: float
    size: float
    tif: str = "IOC"  # IOC, FOK, GTC
    client_order_id: str | None = None


@dataclass
class ExecutionPlan:
    intents: List[OrderIntent]
    expected_profit: float
    rationale: str
    plan_id: str | None = None
