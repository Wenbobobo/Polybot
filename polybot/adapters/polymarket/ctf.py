from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MergeRequest:
    market_id: str
    outcome_yes_id: str
    outcome_no_id: str
    size: float  # number of shares to merge into USDC


@dataclass
class SplitRequest:
    market_id: str
    outcome_yes_id: str
    outcome_no_id: str
    usdc_amount: float  # USDC to split into YES/NO shares


@dataclass
class CtfAck:
    tx_id: str
    accepted: bool
    reason: Optional[str] = None


class FakeCTF:
    def __init__(self):
        self._seq = 0

    def merge(self, req: MergeRequest) -> CtfAck:
        self._seq += 1
        if req.size <= 0:
            return CtfAck(tx_id=f"ctf-{self._seq}", accepted=False, reason="invalid_size")
        return CtfAck(tx_id=f"ctf-{self._seq}", accepted=True)

    def split(self, req: SplitRequest) -> CtfAck:
        self._seq += 1
        if req.usdc_amount <= 0:
            return CtfAck(tx_id=f"ctf-{self._seq}", accepted=False, reason="invalid_amount")
        return CtfAck(tx_id=f"ctf-{self._seq}", accepted=True)


def build_ctf(kind: str = "fake", **kwargs) -> FakeCTF:
    kind = (kind or "fake").lower()
    if kind == "fake":
        return FakeCTF()
    # Placeholder for real CTF client wiring (merge/split on-chain)
    raise NotImplementedError("Real CTF client is not wired in Phase 1")

