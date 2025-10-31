from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_schema_has_outcomes_snapshots_orders_fills():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    assert schema.table_exists(con, "outcomes")
    assert schema.table_exists(con, "orderbook_snapshots")
    assert schema.table_exists(con, "orders")
    assert schema.table_exists(con, "fills")

