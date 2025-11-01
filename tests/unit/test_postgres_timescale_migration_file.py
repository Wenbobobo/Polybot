from pathlib import Path


def test_timescale_migration_file_exists_and_has_extension():
    p = Path("migrations/postgres/010_timescale.sql")
    text = p.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in text
    assert "create_hypertable('orderbook_events'" in text or "create_hypertable('orderbook_snapshots'" in text

