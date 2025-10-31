from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor


def test_manual_snapshot_and_prune_events():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    ing.process({"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}, ts_ms=1000)
    ing.process({"type": "delta", "seq": 11, "bids": [[0.41, 1.0]]}, ts_ms=1100)
    ing.persist_snapshot_now(ts_ms=1200)
    # prune earlier than 1100 should delete the delta
    pruned = ing.prune_events_before(1150)
    assert pruned == 1
    remaining = con.execute("SELECT COUNT(*) FROM orderbook_events").fetchone()[0]
    assert remaining == 0
    snaps = con.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0]
    assert snaps == 2

