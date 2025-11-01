from polybot.cli import commands as cmds


class StubAdapter:
    def approve_usdc(self, amount: float):
        return {"tx": "0xusdc", "amount": amount}

    def approve_outcome(self, token: str, amount: float):
        return {"tx": "0xout", "token": token, "amount": amount}


def test_cli_allowances_success(monkeypatch):
    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: StubAdapter())
    out1 = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="k", amount=123.0)
    assert out1.startswith("approve_usdc submitted:")
    out2 = cmds.cmd_relayer_approve_outcome(base_url="u", private_key="k", token_address="0xabc", amount=3.0)
    assert out2.startswith("approve_outcome submitted:")

