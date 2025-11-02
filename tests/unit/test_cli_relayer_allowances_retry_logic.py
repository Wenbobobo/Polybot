from polybot.cli import commands as cmds
from polybot.observability.metrics import (
    get_counter_labelled,
    reset as metrics_reset,
)


class FlakyRelayer:
    def __init__(self, fail_times: int, kind: str):
        self.fail_times = fail_times
        self.kind = kind
        self.calls = 0

    def approve_usdc(self, amount: float):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("transient")
        return {"tx": "0x1"}

    def approve_outcome(self, token: str, amount: float):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("transient")
        return {"tx": "0x2"}


def test_allow_usdc_retries_then_succeeds(monkeypatch):
    metrics_reset()
    rel = FlakyRelayer(fail_times=1, kind="usdc")
    monkeypatch.setattr(cmds, "_try_build_real_relayer", lambda *a, **k: rel)
    # avoid sleeps
    import time as _t

    monkeypatch.setattr(_t, "sleep", lambda s: None)
    out = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="0x" + "1" * 64, amount=1.0, retries=2, backoff_ms=0)
    assert out.startswith("approve_usdc submitted:")
    # attempts: 2 (1 failure + 1 success)
    assert get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"}) == 2
    assert get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"}) == 1
    assert get_counter_labelled("relayer_allowance_success", {"kind": "usdc"}) == 1


def test_allow_outcome_exhausts_retries(monkeypatch):
    metrics_reset()
    rel = FlakyRelayer(fail_times=5, kind="outcome")
    monkeypatch.setattr(cmds, "_try_build_real_relayer", lambda *a, **k: rel)
    import time as _t

    monkeypatch.setattr(_t, "sleep", lambda s: None)
    out = cmds.cmd_relayer_approve_outcome(base_url="u", private_key="0x" + "2" * 64, token_address="0xabc", amount=1.0, retries=1, backoff_ms=0)
    assert out.startswith("relayer unavailable:")
    # attempts: retries + 1
    assert get_counter_labelled("relayer_allowance_attempts", {"kind": "outcome"}) == 2
    assert get_counter_labelled("relayer_allowance_errors", {"kind": "outcome"}) == 2
    assert get_counter_labelled("relayer_allowance_success", {"kind": "outcome"}) == 0

