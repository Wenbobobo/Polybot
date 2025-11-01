from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer


class StubCamel:
    def approveUsdc(self, amount: float):
        return {"tx": "0xusdc", "amount": amount}

    def approveOutcome(self, token: str, amount: float):
        return {"tx": "0xoutcome", "token": token, "amount": amount}


def test_pyclob_adapter_supports_camelcase_allowances():
    adapter = PyClobRelayer(StubCamel())
    r1 = adapter.approve_usdc(5.0)
    assert r1["tx"] == "0xusdc"
    r2 = adapter.approve_outcome("0xabc", 1.0)
    assert r2["tx"] == "0xoutcome" and r2["token"] == "0xabc"

