from polybot.adapters.polymarket.ctf import FakeCTF, MergeRequest, SplitRequest


def test_fake_ctf_merge_and_split_success_and_failure():
    ctf = FakeCTF()
    ok = ctf.merge(MergeRequest(market_id="m1", outcome_yes_id="y", outcome_no_id="n", size=10.0))
    assert ok.accepted and ok.tx_id
    bad = ctf.merge(MergeRequest(market_id="m1", outcome_yes_id="y", outcome_no_id="n", size=0.0))
    assert not bad.accepted and bad.reason == "invalid_size"
    ok2 = ctf.split(SplitRequest(market_id="m1", outcome_yes_id="y", outcome_no_id="n", usdc_amount=5.0))
    assert ok2.accepted and ok2.tx_id
    bad2 = ctf.split(SplitRequest(market_id="m1", outcome_yes_id="y", outcome_no_id="n", usdc_amount=-1.0))
    assert not bad2.accepted and bad2.reason == "invalid_amount"

