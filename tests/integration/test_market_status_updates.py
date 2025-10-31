from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor


def test_market_status_updated_on_process():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    ing.process({"type": "snapshot", "seq": 10, "bids": [[0.4, 1.0]], "asks": [[0.6, 1.0]]}, ts_ms=1000)
    ing.process({"type": "delta", "seq": 11, "bids": [[0.41, 1.0]]}, ts_ms=1100)
    row = con.execute("SELECT market_id, last_seq, last_update_ts_ms, snapshots, deltas FROM market_status WHERE market_id='m1'").fetchone()
    assert row is not None
    assert row[1] == 11
    assert row[3] >= 1
    assert row[4] >= 1

