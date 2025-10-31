from pathlib import Path

from polybot.config import load_config


def test_load_default_config():
    cfg = load_config(Path("config/default.toml"))
    assert cfg.polymarket_gamma_base_url
    assert cfg.polymarket_relayer_base_url
    assert cfg.db_url.startswith("sqlite:///") or cfg.db_url == ":memory:"
    assert cfg.thresholds_min_profit_usdc == 0.02
    assert cfg.strategy_dutch_book is True
    assert cfg.strategy_spread_capture is True
    assert cfg.strategy_conversions is False
    assert cfg.strategy_news is False

