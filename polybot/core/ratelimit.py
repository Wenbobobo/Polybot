from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    capacity: float
    refill_per_sec: float
    tokens: float = 0.0
    last_refill_ms: int = 0

    def _refill(self, now_ms: int) -> None:
        if self.last_refill_ms == 0:
            self.last_refill_ms = now_ms
            self.tokens = min(self.capacity, self.tokens)
            return
        delta_s = max(0.0, (now_ms - self.last_refill_ms) / 1000.0)
        if delta_s <= 0:
            return
        self.tokens = min(self.capacity, self.tokens + delta_s * self.refill_per_sec)
        self.last_refill_ms = now_ms

    def allow(self, amount: float = 1.0, now_ms: int | None = None) -> bool:
        now_ms = now_ms or int(time.time() * 1000)
        self._refill(now_ms)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

