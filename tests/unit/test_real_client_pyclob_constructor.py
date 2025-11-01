import sys

from polybot.adapters.polymarket.real_client import make_pyclob_client


class FakeClobClient:
    def __init__(self, base_url: str, private_key: str, dry_run: bool = True):
        self.base_url = base_url
        self.private_key = private_key
        self.dry_run = dry_run


def test_make_pyclob_client_constructs_with_given_params(monkeypatch):
    # Inject a fake py_clob_client module
    mod = type(sys)("py_clob_client")
    mod.ClobClient = FakeClobClient
    sys.modules["py_clob_client"] = mod
    try:
        c = make_pyclob_client(base_url="https://x", private_key="0xabc", dry_run=False)
        assert isinstance(c, FakeClobClient)
        assert c.base_url == "https://x" and c.private_key == "0xabc" and c.dry_run is False
    finally:
        sys.modules.pop("py_clob_client", None)

