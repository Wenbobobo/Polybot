from polybot.adapters.polymarket.pyclob_adapter import PyClobRelayer


class StubPyClobAllow:
    def approve_usdc(self, amount: float):
        return {"tx": "0xusdc", "amount": amount}

    def approve_outcome(self, token: str, amount: float):
        return {"tx": "0xoutcome", "token": token, "amount": amount}


def test_pyclob_adapter_forwards_allowances_when_available():
    stub = StubPyClobAllow()
    adapter = PyClobRelayer(stub)
    r1 = adapter.approve_usdc(100.0)
    assert r1["tx"] == "0xusdc" and r1["amount"] == 100.0
    r2 = adapter.approve_outcome("0xabc", 10.0)
    assert r2["tx"] == "0xoutcome" and r2["token"] == "0xabc"

