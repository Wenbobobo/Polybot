import sys

from polybot.adapters.polymarket.real_client import make_pyclob_client


class FakeClobClient:
    def __init__(self, base_url: str, private_key: str, dry_run: bool = True, **kwargs):
        self.base_url = base_url
        self.private_key = private_key
        self.dry_run = dry_run
        self.kwargs = kwargs


def test_make_pyclob_client_forwards_extra_kwargs(monkeypatch):
    mod = type(sys)("py_clob_client")
    mod.ClobClient = FakeClobClient
    sys.modules["py_clob_client"] = mod
    try:
        c = make_pyclob_client(base_url="https://x", private_key="0xabc", dry_run=True, chain_id=137, timeout=5.0)
        assert c.kwargs.get("chain_id") == 137
        assert c.kwargs.get("timeout") == 5.0
    finally:
        sys.modules.pop("py_clob_client", None)

