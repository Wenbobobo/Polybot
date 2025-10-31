from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_orders_indices_present():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_orders_market_status','idx_orders_market')").fetchall()
    names = {r[0] for r in rows}
    assert 'idx_orders_market' in names
    assert 'idx_orders_market_status' in names

