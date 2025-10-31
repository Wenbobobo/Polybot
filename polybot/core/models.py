from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


Side = Literal["bid", "ask"]


@dataclass
class Outcome:
    outcome_id: str
    market_id: str
    name: str
    tick_size: float = 0.01
    min_size: float = 1.0


@dataclass
class Market:
    market_id: str
    title: str
    status: str
    condition_id: Optional[str] = None
    neg_risk_group: Optional[str] = None
    rule_hash: Optional[str] = None
    outcomes: List[Outcome] | None = None


@dataclass
class Level:
    price: float
    size: float


@dataclass
class OrderBook:
    market_id: str
    seq: int
    bids: Dict[float, float]
    asks: Dict[float, float]

    def best_bid(self) -> Optional[Level]:
        if not self.bids:
            return None
        p = max(self.bids.keys())
        return Level(price=p, size=self.bids[p])

    def best_ask(self) -> Optional[Level]:
        if not self.asks:
            return None
        p = min(self.asks.keys())
        return Level(price=p, size=self.asks[p])

