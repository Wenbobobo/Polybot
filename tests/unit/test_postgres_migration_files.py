from pathlib import Path


def test_postgres_migration_file_exists_and_has_core_tables():
    p = Path("migrations/postgres/001_init.sql")
    text = p.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS markets" in text
    assert "CREATE TABLE IF NOT EXISTS outcomes" in text
    assert "CREATE TABLE IF NOT EXISTS orders" in text
    assert "CREATE TABLE IF NOT EXISTS exec_audit" in text

