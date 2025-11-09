from polybot.cli import commands as cmds
from polybot.observability.metrics import (
    get_counter_labelled,
    reset as metrics_reset,
)


class FlakyAllowanceRelayer:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times

    def get_balance_allowance(self, params):
        return {"token": getattr(params, "token_id", ""), "allowance": "5"}

    def update_balance_allowance(self, params):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("transient")
        return {"updated": True, "token": getattr(params, "token_id", "")}


def test_allow_usdc_retries_then_succeeds(monkeypatch):
    metrics_reset()
    rel = FlakyAllowanceRelayer(fail_times=1)
    monkeypatch.setattr(cmds, "_build_real_relayer_cli", lambda *a, **k: rel)
    monkeypatch.setattr(cmds, "_collect_builder_kwargs", lambda cfg: {})
    monkeypatch.setattr(cmds, "_ensure_builder_ready", lambda cfg, kwargs: (True, None))
    import time as _t

    monkeypatch.setattr(_t, "sleep", lambda s: None)
    out = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="0x" + "1" * 64, amount=1.0, retries=2, backoff_ms=0)
    assert out.startswith("allowance_usdc ok")
    assert get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"}) == 2
    assert get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"}) == 1
    assert get_counter_labelled("relayer_allowance_success", {"kind": "usdc"}) == 1


def test_allow_outcome_exhausts_retries(monkeypatch):
    metrics_reset()
    rel = FlakyAllowanceRelayer(fail_times=5)
    monkeypatch.setattr(cmds, "_build_real_relayer_cli", lambda *a, **k: rel)
    monkeypatch.setattr(cmds, "_collect_builder_kwargs", lambda cfg: {})
    monkeypatch.setattr(cmds, "_ensure_builder_ready", lambda cfg, kwargs: (True, None))
    import time as _t

    monkeypatch.setattr(_t, "sleep", lambda s: None)
    out = cmds.cmd_relayer_approve_outcome(base_url="u", private_key="0x" + "2" * 64, token_address="0xabc", amount=1.0, retries=1, backoff_ms=0)
    assert out.startswith("relayer unavailable:")
    assert get_counter_labelled("relayer_allowance_attempts", {"kind": "outcome"}) == 2
    assert get_counter_labelled("relayer_allowance_errors", {"kind": "outcome"}) == 2
    assert get_counter_labelled("relayer_allowance_success", {"kind": "outcome"}) == 0
