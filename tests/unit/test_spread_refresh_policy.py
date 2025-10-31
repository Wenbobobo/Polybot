from polybot.strategy.spread import should_refresh_quotes


def test_refresh_on_tick_move():
    assert should_refresh_quotes(0.40, 0.47, 0.41, 0.47, tick_size=0.01, max_mid_jump=0.03) is True
    assert should_refresh_quotes(0.40, 0.47, 0.40, 0.46, tick_size=0.01, max_mid_jump=0.03) is True


def test_no_refresh_when_stable():
    assert should_refresh_quotes(0.40, 0.47, 0.40, 0.47, tick_size=0.01, max_mid_jump=0.03) is False


def test_refresh_on_large_mid_jump():
    assert should_refresh_quotes(0.40, 0.47, 0.49, 0.51, tick_size=0.01, max_mid_jump=0.03) is True

