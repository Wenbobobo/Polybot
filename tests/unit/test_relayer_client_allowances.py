from polybot.adapters.polymarket.relayer import RelayerClient


class StubAllow:
    def approve_usdc(self, amount: float):
        return {"tx": "0xusdc", "amount": amount}

    def approveOutcome(self, token: str, amount: float):
        return {"tx": "0xout", "token": token, "amount": amount}


def test_relayer_client_allowances_snake_and_camel():
    rc = RelayerClient(StubAllow())
    r1 = rc.approve_usdc(5.0)
    assert r1["tx"] == "0xusdc"
    r2 = rc.approve_outcome("0xabc", 1.0)
    assert r2["tx"] == "0xout" and r2["token"] == "0xabc"

