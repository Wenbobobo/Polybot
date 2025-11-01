from pathlib import Path

from polybot.config import load_config


def test_load_default_config(tmp_path: Path):
    # Create a minimal config TOML in a temp path instead of relying on repo files
    p = tmp_path / "testcfg.toml"
    p.write_text(
        """
        [polymarket]
        gamma_base_url = "https://gamma-api.polymarket.com"
        relayer_base_url = "https://clob.polymarket.com"

        [db]
        url = ":memory:"
        wal = true

        [strategy]
        dutch_book = true
        spread_capture = true
        conversions = false
        news = false

        [thresholds]
        min_profit_usdc = 0.02
        """,
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.polymarket_gamma_base_url == "https://gamma-api.polymarket.com"
    assert cfg.polymarket_relayer_base_url == "https://clob.polymarket.com"
    assert cfg.db_url == ":memory:"
    assert cfg.thresholds_min_profit_usdc == 0.02
    assert cfg.strategy_dutch_book is True
    assert cfg.strategy_spread_capture is True
    assert cfg.strategy_conversions is False
    assert cfg.strategy_news is False
