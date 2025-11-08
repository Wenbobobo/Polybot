import sys

from polybot.adapters.polymarket.real_client import make_pyclob_client


class _CaptureClob:
    def __init__(self, *args, **kwargs):
        type(self).kwargs = kwargs


def _install_fake_module(monkeypatch):
    mod = type(sys)("py_clob_client")
    mod.ClobClient = _CaptureClob  # type: ignore[attr-defined]
    sys.modules["py_clob_client"] = mod  # type: ignore
    return mod


def test_make_client_attaches_local_builder(monkeypatch):
    _install_fake_module(monkeypatch)
    try:
        make_pyclob_client(
            base_url="https://x",
            private_key="0xabc",
            dry_run=False,
            builder_api_key="k",
            builder_api_secret="s",
            builder_api_passphrase="p",
        )
        kwargs = getattr(_CaptureClob, "kwargs")
        assert "builder_config" in kwargs
        cfg = kwargs["builder_config"]
        assert getattr(cfg, "local_builder_creds").key == "k"
    finally:
        sys.modules.pop("py_clob_client", None)


def test_make_client_attaches_remote_builder(monkeypatch):
    _install_fake_module(monkeypatch)
    try:
        make_pyclob_client(
            base_url="https://x",
            private_key="0xabc",
            dry_run=False,
            builder_remote_url="https://builder",
            builder_remote_token="tok",
        )
        cfg = getattr(_CaptureClob, "kwargs")["builder_config"]
        assert getattr(cfg, "remote_builder_config").url == "https://builder"
    finally:
        sys.modules.pop("py_clob_client", None)
