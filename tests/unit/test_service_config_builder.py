from pathlib import Path

from polybot.service.config import load_service_config


def test_service_config_builder_local(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        private_key = "0x0"
        [relayer.builder]
        mode = "local"
        api_key = "k"
        api_secret = "s"
        api_passphrase = "p"
        """,
        encoding="utf-8",
    )
    sc = load_service_config(str(cfg))
    assert sc.relayer_builder is not None
    builder = sc.relayer_builder
    assert builder.api_key == "k"
    assert builder.mode == "local"


def test_service_config_builder_overlay(tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    secrets = tmp_path / "secrets.local.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        private_key = "0x0"
        """,
        encoding="utf-8",
    )
    secrets.write_text(
        """
        [relayer]
        private_key = "0x1"
        [relayer.builder]
        mode = "remote"
        url = "https://builder"
        token = "token"
        """,
        encoding="utf-8",
    )
    sc = load_service_config(str(cfg))
    assert sc.relayer_private_key == "0x1"
    assert sc.relayer_builder is not None
    builder = sc.relayer_builder
    assert builder.mode == "remote"
    assert builder.url == "https://builder"
    assert builder.token == "token"
