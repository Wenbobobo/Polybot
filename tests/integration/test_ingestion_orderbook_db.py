import sqlite3
from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.ingestion.orderbook import OrderbookIngestor


def test_ingestion_writes_snapshot_and_events():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    ing = OrderbookIngestor(con, "m1")
    ing.process({"type": "snapshot", "seq": 10, "bids": [[0.4, 100.0]], "asks": [[0.47, 50.0]]}, ts_ms=1000)
    ing.process({"type": "delta", "seq": 11, "bids": [[0.41, 20.0]], "asks": [[0.47, -50.0], [0.46, 40.0]]}, ts_ms=1100)

    cur = con.execute("SELECT COUNT(*) FROM orderbook_snapshots WHERE market_id='m1'")
    assert cur.fetchone()[0] == 1
    cur = con.execute("SELECT COUNT(*) FROM orderbook_events WHERE market_id='m1'")
    assert cur.fetchone()[0] == 3

