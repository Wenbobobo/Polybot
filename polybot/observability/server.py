from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional, Tuple

from .prometheus import export_text


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/metrics":
            body = export_text().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        # Suppress default stdout logging
        return


def start_metrics_server(host: str = "127.0.0.1", port: int = 0) -> Tuple[HTTPServer, Thread]:
    server = HTTPServer((host, port), _MetricsHandler)
    th = Thread(target=server.serve_forever, daemon=True)
    th.start()
    return server, th

def stop_metrics_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()
