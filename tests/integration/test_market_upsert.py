import json
from pathlib import Path

from polybot.storage.db import connect_sqlite
from polybot.storage import schema
from polybot.adapters.polymarket.gamma import GammaClient
from polybot.storage.markets import upsert_markets


def test_upsert_markets_from_gamma_fixture(tmp_path: Path):
    raw = json.loads(Path("tests/fixtures/gamma_markets_sample.json").read_text(encoding="utf-8"))
    norm = GammaClient.normalize_markets(raw)
    con = connect_sqlite(":memory:")
    schema.create_all(con)
    upsert_markets(con, norm)

    cnt_m = con.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
    cnt_o = con.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
    assert cnt_m == 2 and cnt_o >= 3

