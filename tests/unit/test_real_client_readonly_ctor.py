import sys

from polybot.adapters.polymarket.real_client import make_pyclob_client


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):  # noqa: D401
        self.calls.append((args, kwargs))


def test_make_pyclob_client_readonly_prefers_positional_host(monkeypatch):
    rec = Recorder()

    class FakeClobClient:
        def __init__(self, *args, **kwargs):  # noqa: D401
            rec(*args, **kwargs)

    mod = type(sys)("py_clob_client")
    mod.ClobClient = FakeClobClient
    sys.modules["py_clob_client"] = mod
    try:
        c = make_pyclob_client(base_url="https://x", private_key="", dry_run=True)
        assert rec.calls, "should construct client"
        args, kwargs = rec.calls[0]
        # First arg should be host/base_url positional
        assert args and args[0] == "https://x"
        assert not kwargs  # no stray kwargs in readonly path
    finally:
        sys.modules.pop("py_clob_client", None)

