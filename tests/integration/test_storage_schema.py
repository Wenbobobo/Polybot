from polybot.storage.db import connect_sqlite
from polybot.storage import schema


def test_create_schema_sqlite_memory():
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    assert schema.table_exists(con, "markets")
    assert schema.table_exists(con, "orderbook_events")

