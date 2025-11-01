from pathlib import Path

from polybot.service.config import load_service_config


def test_service_config_overlays_secrets_local(tmp_path: Path):
    cfg = tmp_path / "m.toml"
    sec = tmp_path / "secrets.local.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        base_url = "https://clob.polymarket.com"
        dry_run = true
        private_key = ""
        """,
        encoding="utf-8",
    )
    sec.write_text(
        """
        [relayer]
        private_key = "0xdeadbeef"
        dry_run = false
        """,
        encoding="utf-8",
    )
    c = load_service_config(str(cfg))
    assert c.relayer_private_key == "0xdeadbeef"
    assert c.relayer_dry_run is False

