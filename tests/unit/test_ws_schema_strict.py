import pytest
from pydantic import ValidationError

from polybot.adapters.polymarket.schemas import SnapshotMsg, DeltaMsg


def test_snapshot_rejects_bad_price_arrays():
    with pytest.raises(ValidationError):
        SnapshotMsg(type="snapshot", seq=1, bids=[[0.5]], asks=[[0.6, 1.0]])


def test_delta_rejects_bad_arrays():
    with pytest.raises(ValidationError):
        DeltaMsg(type="delta", seq=2, bids=[[0.1, 1.0, 2.0]])

