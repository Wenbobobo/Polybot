from pydantic import ValidationError
from polybot.adapters.polymarket.schemas import MarketSchema, SnapshotMsg, DeltaMsg


def test_market_schema_validates():
    m = MarketSchema(id="m1", title="T", status="active", outcomes=[{"id": "o1", "name": "Yes"}])
    assert m.id == "m1" and m.outcomes[0].name == "Yes"


def test_snapshot_msg_validation():
    s = SnapshotMsg(type="snapshot", seq=10, bids=[[0.4, 100.0]], asks=[[0.6, 50.0]])
    assert s.seq == 10 and s.bids[0][0] == 0.4
    try:
        SnapshotMsg(type="snapshot", seq=-1, bids=[], asks=[])
        assert False, "Validation should fail for negative seq"
    except ValidationError:
        pass


def test_delta_msg_optional_fields():
    d = DeltaMsg(type="delta", seq=11)
    assert d.bids is None and d.asks is None

