import json
from pathlib import Path

from polybot.adapters.polymarket.gamma import GammaClient


def test_gamma_normalize_sample_fixture():
    raw = json.loads(Path("tests/fixtures/gamma_markets_sample.json").read_text(encoding="utf-8"))
    norm = GammaClient.normalize_markets(raw)
    assert len(norm) == 2
    m1 = next(m for m in norm if m["market_id"] == "mkt-1")
    assert m1["title"] == "Will X happen?"
    assert m1["status"] == "active"
    assert {o["name"] for o in m1["outcomes"]} == {"Yes", "No"}

