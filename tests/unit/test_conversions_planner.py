from polybot.strategy.conversions import Holdings, should_merge, should_split


def test_should_merge_and_split_thresholds():
    h = Holdings(yes=10.0, no=9.0, usdc=50.0)
    # merge when we have pairs and gas cost does not exceed threshold compared to min profit
    assert should_merge(h, price_yes=0.5, price_no=0.5, min_profit_usdc=0.0, gas_cost_usdc=0.1)
    assert not should_merge(h, price_yes=0.5, price_no=0.5, min_profit_usdc=1.0, gas_cost_usdc=2.0)

    # split requires sufficient USDC and surplus over gas threshold
    assert should_split(h, usdc_to_use=10.0, min_profit_usdc=0.0, gas_cost_usdc=0.1)
    assert not should_split(h, usdc_to_use=100.0, min_profit_usdc=0.0, gas_cost_usdc=0.0)

