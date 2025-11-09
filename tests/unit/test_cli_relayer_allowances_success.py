from polybot.cli import commands as cmds


class StubAllowanceRelayer:
    def __init__(self):
        self.calls = []

    def get_balance_allowance(self, params):
        token = getattr(params, "token_id", "")
        kind = "usdc" if not token else "outcome"
        return {"kind": kind, "token": token, "allowance": "123"}

    def update_balance_allowance(self, params):
        token = getattr(params, "token_id", "")
        self.calls.append(token or "usdc")
        return {"updated": True, "token": token or "usdc"}


def test_cli_allowances_success(monkeypatch):
    stub = StubAllowanceRelayer()
    monkeypatch.setattr(cmds, "_build_real_relayer_cli", lambda *a, **k: stub)
    monkeypatch.setattr(cmds, "_collect_builder_kwargs", lambda cfg: {})
    monkeypatch.setattr(cmds, "_ensure_builder_ready", lambda cfg, kwargs: (True, None))
    out1 = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="0x" + "1" * 64, amount=123.0)
    assert out1.startswith("allowance_usdc ok")
    out2 = cmds.cmd_relayer_approve_outcome(base_url="u", private_key="0x" + "2" * 64, token_address="0xabc", amount=3.0)
    assert out2.startswith("allowance_outcome ok")
    assert stub.calls == ["usdc", "0xabc"]
