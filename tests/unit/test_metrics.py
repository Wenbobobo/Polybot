from polybot.observability.metrics import inc, get_counter, Timer


def test_counters_and_timer():
    inc("x", 3)
    assert get_counter("x") >= 3
    with Timer("foo"):
        pass
    assert get_counter("foo_count") == 1
    assert get_counter("foo_ms_sum") >= 0

