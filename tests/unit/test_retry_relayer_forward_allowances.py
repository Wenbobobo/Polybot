from polybot.adapters.polymarket.relayer import RetryRelayer


class Inner:
    def approve_usdc(self, amount: float):
        return {"tx": "0x1"}

    def approve_outcome(self, token: str, amount: float):
        return {"tx": "0x2"}


def test_retry_relayer_forwards_allowances_methods():
    rr = RetryRelayer(Inner(), max_retries=0)
    assert rr.approve_usdc(1.0)["tx"] == "0x1"
    assert rr.approve_outcome("0xabc", 1.0)["tx"] == "0x2"

