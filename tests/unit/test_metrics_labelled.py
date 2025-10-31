from polybot.observability.metrics import inc_labelled, get_counter_labelled


def test_labelled_counters():
    inc_labelled("foo", {"market": "m1"}, 2)
    inc_labelled("foo", {"market": "m2"}, 3)
    assert get_counter_labelled("foo", {"market": "m1"}) == 2
    assert get_counter_labelled("foo", {"market": "m2"}) == 3

