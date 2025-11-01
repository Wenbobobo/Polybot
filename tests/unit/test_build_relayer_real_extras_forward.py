import sys


def test_build_relayer_real_forwards_extras(monkeypatch):
    from polybot.adapters.polymarket import relayer as r

    seen = {}

    # Create a fake real_client module with make_pyclob_client
    mod_name = "polybot.adapters.polymarket.real_client"
    fake_mod = type(sys)(mod_name)

    def fake_make_client(base_url: str, private_key: str, dry_run: bool = True, **kw):
        nonlocal seen
        seen = {"base_url": base_url, "private_key": private_key, "dry_run": dry_run, **kw}

        class _C:
            def place_orders(self, x):
                return []

            def cancel_orders(self, ids):
                return []

        return _C()

    fake_mod.make_pyclob_client = fake_make_client  # type: ignore[attr-defined]
    sys.modules[mod_name] = fake_mod
    try:
        obj = r.build_relayer("real", base_url="u", private_key="k", dry_run=True, chain_id=137, timeout_s=5.5)
    finally:
        sys.modules.pop(mod_name, None)
    # Verify extras forwarded
    assert seen.get("chain_id") == 137
    assert seen.get("timeout_s") == 5.5
    assert seen["base_url"] == "u" and seen["private_key"] == "k" and seen["dry_run"] is True
    # And adapter returned exposes place_orders
    assert hasattr(obj, "place_orders")
