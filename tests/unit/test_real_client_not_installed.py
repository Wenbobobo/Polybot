import pytest

from polybot.adapters.polymarket.real_client import make_pyclob_client


def test_make_pyclob_client_raises_when_dependency_missing():
    with pytest.raises(NotImplementedError):
        make_pyclob_client(base_url="https://clob.polymarket.com", private_key="0xdeadbeef", dry_run=True)

