from polybot.observability.server import start_metrics_server, stop_metrics_server
from polybot.observability.metrics import inc, inc_labelled
import httpx


def test_metrics_server_status_json():
    inc("foo_total", 1)
    inc_labelled("bar_events", {"market": "m1"}, 2)
    server, _ = start_metrics_server("127.0.0.1", 0)
    port = server.server_address[1]
    try:
        with httpx.Client(trust_env=False, timeout=5.0) as client:
            r = client.get(f"http://127.0.0.1:{port}/status")
        assert r.status_code == 200
        data = r.json()
        assert "counters" in data and "labelled" in data
        assert data["counters"].get("foo_total", 0) >= 1
    finally:
        stop_metrics_server(server)

