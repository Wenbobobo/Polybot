from polybot.cli import commands as cmds
from polybot.observability.metrics import get_counter_labelled


class BoomAdapter:
    def __init__(self):
        self.calls = 0

    def get_balance_allowance(self, params):
        return {"allowance": "10"}

    def update_balance_allowance(self, params):
        self.calls += 1
        raise RuntimeError("rate limited")


class OkAdapter:
    def get_balance_allowance(self, params):
        return {"allowance": "10"}

    def update_balance_allowance(self, params):
        return {"updated": True}


def _patch_builder_ready(monkeypatch):
    monkeypatch.setattr(cmds, "_ensure_builder_ready", lambda cfg, kwargs: (True, None))
    monkeypatch.setattr(cmds, "_collect_builder_kwargs", lambda cfg: {})


def test_allowance_cli_increments_metrics_on_retry(monkeypatch):
    _patch_builder_ready(monkeypatch)
    monkeypatch.setattr(cmds, "_build_real_relayer_cli", lambda *a, **k: BoomAdapter())
    before_a = get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"})
    before_e = get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"})
    out = cmds.cmd_relayer_approve_usdc(base_url="u", private_key="0x" + "1" * 64, amount=1.0, retries=1, backoff_ms=0)
    after_a = get_counter_labelled("relayer_allowance_attempts", {"kind": "usdc"})
    after_e = get_counter_labelled("relayer_allowance_errors", {"kind": "usdc"})
    assert after_a >= before_a + 2  # initial + retry
    assert after_e >= before_e + 2
    assert out.startswith("relayer unavailable:")


def test_allowance_cli_success_increments_success(monkeypatch):
    _patch_builder_ready(monkeypatch)
    monkeypatch.setattr(cmds, "_build_real_relayer_cli", lambda *a, **k: OkAdapter())
    before = get_counter_labelled("relayer_allowance_success", {"kind": "usdc"})
    cmds.cmd_relayer_approve_usdc(base_url="u", private_key="0x" + "1" * 64, amount=1.0, retries=0)
    after = get_counter_labelled("relayer_allowance_success", {"kind": "usdc"})
    assert after == before + 1
