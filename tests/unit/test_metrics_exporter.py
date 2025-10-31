from polybot.observability.metrics import inc, inc_labelled, get_counter, get_counter_labelled, reset
from polybot.observability.prometheus import export_text


def test_metrics_reset_and_export_text():
    # Seed some metrics
    inc("foo_total", 3)
    inc_labelled("bar", {"market": "m1"}, 2)
    inc_labelled("bar", {"market": "m2"}, 5)

    # Export to Prometheus text format
    text = export_text()
    assert "# TYPE foo_total counter" in text
    assert "foo_total 3" in text
    # Label formatting: {k="v"}
    assert "bar{market=\"m1\"} 2" in text
    assert "bar{market=\"m2\"} 5" in text

    # Reset and verify cleared
    reset()
    assert get_counter("foo_total") == 0
    assert get_counter_labelled("bar", {"market": "m1"}) == 0
    # Export should reflect cleared state (no lines for zeroed counters)
    text2 = export_text()
    assert "foo_total 3" not in text2
    assert "bar{market=\"m1\"}" not in text2

