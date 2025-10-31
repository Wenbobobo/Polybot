from pathlib import Path
import textwrap

from polybot.config import load_config_stack


def test_load_config_stack_merges_files(tmp_path: Path):
    base = tmp_path / "base.toml"
    override = tmp_path / "override.toml"
    base.write_text(textwrap.dedent(
        """
        [polymarket]
        gamma_base_url = "https://a"
        [strategy]
        dutch_book = true
        spread_capture = false
        """
    ), encoding="utf-8")
    override.write_text(textwrap.dedent(
        """
        [polymarket]
        gamma_base_url = "https://b"
        [strategy]
        spread_capture = true
        """
    ), encoding="utf-8")

    cfg = load_config_stack([base, override])
    assert cfg.polymarket_gamma_base_url == "https://b"
    assert cfg.strategy_dutch_book is True
    assert cfg.strategy_spread_capture is True

