from polybot.observability.metrics import inc_labelled, reset as metrics_reset
from polybot.observability.prometheus import export_text


def test_prometheus_label_escaping_quotes_and_backslashes():
    metrics_reset()
    inc_labelled("test_metric", {"a": "x\"y\\z"}, 1)
    text = export_text()
    # Expect escaped quotes and backslashes in output
    assert 'test_metric{a="x\\\"y\\\\z"} 1' in text

