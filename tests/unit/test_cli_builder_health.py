from pathlib import Path
from types import SimpleNamespace

from polybot.cli import commands as cmds


class _StubClient:
    def __init__(self, can_auth: bool = True):
        self._can_auth = can_auth
        self.builder_config = SimpleNamespace(
            get_builder_type=lambda: SimpleNamespace(value="LOCAL")
        )

    def can_builder_auth(self) -> bool:
        return self._can_auth

    def get_address(self) -> str:
        return "0x" + "a" * 40


class _StubRelayer:
    def __init__(self, can_auth: bool = True):
        self._client = _StubClient(can_auth=can_auth)


def _write_base_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url = ":memory:"

        [relayer]
        type = "real"
        private_key = "0x1111111111111111111111111111111111111111111111111111111111111111"
        base_url = "https://clob.polymarket.com"
        dry_run = true

        [relayer.builder]
        mode = "local"
        api_key = "k"
        api_secret = "s"
        api_passphrase = "p"
        """,
        encoding="utf-8",
    )
    return cfg


def test_builder_health_ok(monkeypatch, tmp_path: Path):
    cfg = _write_base_config(tmp_path)
    monkeypatch.setattr(cmds, "build_relayer", lambda *a, **k: _StubRelayer(), raising=True)
    out = cmds.cmd_builder_health(str(cfg))
    assert out.startswith("builder ok")


def test_builder_health_missing_config(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "svc.toml"
    cfg.write_text(
        """
        [service]
        db_url=":memory:"

        [relayer]
        type="real"
        private_key="0x1111111111111111111111111111111111111111111111111111111111111111"
        """,
        encoding="utf-8",
    )
    out = cmds.cmd_builder_health(str(cfg))
    assert "builder not ready" in out
