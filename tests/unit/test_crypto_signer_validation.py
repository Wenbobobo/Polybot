import pytest

from polybot.adapters.polymarket.crypto import is_valid_private_key, derive_address_like


def test_is_valid_private_key_checks_format():
    assert is_valid_private_key("0x" + "a" * 64)
    assert not is_valid_private_key(123)  # type: ignore[arg-type]
    assert not is_valid_private_key("")
    assert not is_valid_private_key("0xdead")
    assert not is_valid_private_key("zz" + "0" * 64)


def test_derive_address_like_works_for_valid_pk():
    pk = "0x" + ("01" * 32)
    addr = derive_address_like(pk)
    assert addr.startswith("0x") and len(addr) == 42
    with pytest.raises(ValueError):
        derive_address_like("0xdeadbeef")

