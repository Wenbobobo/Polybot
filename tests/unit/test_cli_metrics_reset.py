from polybot.cli import commands as cmds
from polybot.observability.metrics import inc, get_counter


def test_cli_metrics_reset_clears_counters():
    inc("foo", 3)
    assert get_counter("foo") == 3
    out = cmds.cmd_metrics_reset()
    assert out == "OK: metrics reset"
    assert get_counter("foo") == 0

