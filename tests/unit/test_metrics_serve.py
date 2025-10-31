from polybot.observability.metrics import inc
from polybot.observability.server import start_metrics_server, stop_metrics_server
import httpx


def test_metrics_serve_http():
    inc("served_total", 1)
    server, _ = start_metrics_server("127.0.0.1", 0)
    port = server.server_address[1]
    try:
        with httpx.Client(trust_env=False, timeout=5.0) as client:
            r = client.get(f"http://127.0.0.1:{port}/metrics")
        assert r.status_code == 200
        assert "served_total" in r.text
    finally:
        stop_metrics_server(server)
