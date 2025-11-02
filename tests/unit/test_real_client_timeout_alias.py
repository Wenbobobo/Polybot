import types

from polybot.adapters.polymarket.real_client import make_pyclob_client


def test_make_pyclob_client_maps_timeout_s_to_timeout(monkeypatch):
    seen = {}

    class FakeClob:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            seen.update(kwargs)

    mod = types.SimpleNamespace(ClobClient=FakeClob)
    # Monkeypatch import within make_pyclob_client by injecting into sys.modules
    import sys

    sys.modules['py_clob_client'] = mod  # type: ignore
    try:
        make_pyclob_client(base_url="https://x", private_key="0xabc", dry_run=True, chain_id=137, timeout_s=7.5)
        assert seen.get("timeout") == 7.5
        # Ensure original timeout_s key is not forwarded
        assert "timeout_s" not in seen
        # Chain id still forwarded
        assert seen.get("chain_id") == 137
    finally:
        sys.modules.pop('py_clob_client', None)
