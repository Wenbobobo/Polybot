from pydantic import ValidationError

from polybot.adapters.polymarket.schemas import SnapshotMsg, DeltaMsg


def test_snapshot_accepts_official_like_fields():
    s = SnapshotMsg(
        type="snapshot",
        seq=100,
        bids=[[0.45, 123.0]],
        asks=[[0.55, 10.0]],
        channel="l2",
        market="mkt-1",
        ts_ms=1712345678901,
    )
    assert s.market == "mkt-1" and s.channel == "l2"


def test_delta_accepts_checksum_and_metadata():
    d = DeltaMsg(
        type="delta",
        seq=101,
        bids=[[0.46, 5.0]],
        checksum="deadbeef",
        channel="l2",
        market="mkt-1",
        ts_ms=1712345679901,
    )
    assert d.checksum == "deadbeef" and d.market == "mkt-1"


def test_empty_sides_and_large_arrays():
    s = SnapshotMsg(type="snapshot", seq=0, bids=[], asks=[])
    assert s.seq == 0
    d = DeltaMsg(type="delta", seq=1, bids=[[0.10, 0.0] for _ in range(100)])
    assert len(d.bids or []) == 100

