import os

from polybot.cli.commands import _builder_kwargs_from_env, _builder_kwargs_from_cfg
from polybot.service.config import RelayerBuilderConfig, ServiceConfig, SpreadParams


def _dummy_service_config(builder: RelayerBuilderConfig | None = None) -> ServiceConfig:
    return ServiceConfig(
        db_url=":memory:",
        markets=[],
        default_spread=SpreadParams(),
        relayer_builder=builder,
    )


def test_builder_kwargs_from_env(monkeypatch):
    monkeypatch.setenv("POLY_BUILDER_API_KEY", "k")
    monkeypatch.setenv("POLY_BUILDER_SECRET", "s")
    monkeypatch.setenv("POLY_BUILDER_PASSPHRASE", "p")
    monkeypatch.setenv("POLY_BUILDER_REMOTE_URL", "https://builder")
    monkeypatch.setenv("POLY_BUILDER_TOKEN", "tok")
    kwargs = _builder_kwargs_from_env()
    assert kwargs["builder_api_key"] == "k"
    assert kwargs["builder_remote_url"] == "https://builder"
    assert kwargs["builder_remote_token"] == "tok"


def test_builder_kwargs_from_cfg_local():
    cfg = _dummy_service_config(
        RelayerBuilderConfig(
            mode="local",
            api_key="k",
            api_secret="s",
            api_passphrase="p",
        )
    )
    kwargs = _builder_kwargs_from_cfg(cfg)
    assert kwargs["builder_api_key"] == "k"
    assert "builder_remote_url" not in kwargs


def test_builder_kwargs_from_cfg_remote():
    cfg = _dummy_service_config(
        RelayerBuilderConfig(
            mode="remote",
            url="https://builder",
            token="tok",
        )
    )
    kwargs = _builder_kwargs_from_cfg(cfg)
    assert kwargs["builder_remote_url"] == "https://builder"
    assert kwargs["builder_remote_token"] == "tok"
