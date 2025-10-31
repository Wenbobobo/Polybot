from __future__ import annotations

from typing import Protocol, Dict, Any


class SnapshotProvider(Protocol):
    def get_snapshot(self, market_id: str) -> Dict[str, Any]:
        ...


class FakeSnapshotProvider:
    def __init__(self, snapshot: Dict[str, Any]):
        self.snapshot = dict(snapshot)

    def get_snapshot(self, market_id: str) -> Dict[str, Any]:
        return dict(self.snapshot)

