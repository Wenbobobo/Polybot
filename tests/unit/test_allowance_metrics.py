from polybot.cli import commands as cmds
from polybot.observability.metrics import get_counter_labelled


class BoomAdapter:
    def approve_usdc(self, amount: float):
        raise RuntimeError("rate limited")


def test_allowance_cli_increments_metrics_on_retry(monkeypatch):
    monkeypatch.setattr(cmds, "build_relayer", lambda kind, **kw: BoomAdapter())
    before_a = get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"})
    before_e = get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"})
    out = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="k", amount=1.0, retries=1, backoff_ms=0)
    after_a = get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"})
    after_e = get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"})
    assert after_a >= before_a + 2  # initial + retry
    assert after_e >= before_e + 2
    assert out.startswith("relayer unavailable:")

