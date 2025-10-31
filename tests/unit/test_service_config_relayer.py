from pathlib import Path

from polybot.service.config import load_service_config


def test_service_config_parses_relayer_type(tmp_path: Path):
    cfg = tmp_path / "m.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "fake"
        """,
        encoding="utf-8",
    )
    c = load_service_config(str(cfg))
    assert c.relayer_type == "fake"

