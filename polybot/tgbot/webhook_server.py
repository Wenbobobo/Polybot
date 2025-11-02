from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import json
from typing import Iterable, Optional, Tuple

from .agent import BotAgent


class _TgHandler(BaseHTTPRequestHandler):
    agent: BotAgent
    secret_path: str
    allowed_ids: Optional[Iterable[int]]

    def do_POST(self):  # noqa: N802
        if self.path != self.secret_path:
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            # Simple whitelist check
            uid = None
            try:
                uid = int(((data or {}).get("message", {}) or {}).get("from", {}).get("id"))
            except Exception:
                uid = None
            if self.allowed_ids is not None:
                if uid is None or uid not in set(self.allowed_ids):
                    self.send_response(403)
                    self.end_headers()
                    return
            text = (((data or {}).get("message", {}) or {}).get("text") or "").strip()
            if not text:
                self.send_response(400)
                self.end_headers()
                return
            out = self.agent.handle_text(text)
            body = out.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        # Suppress default stdout logging
        return


def start_tg_server(agent: BotAgent, host: str = "127.0.0.1", port: int = 0, secret_path: str = "/tg", allowed_ids: Optional[Iterable[int]] = None) -> Tuple[HTTPServer, Thread]:
    _TgHandler.agent = agent
    _TgHandler.secret_path = secret_path
    _TgHandler.allowed_ids = list(allowed_ids) if allowed_ids is not None else None
    server = HTTPServer((host, port), _TgHandler)
    th = Thread(target=server.serve_forever, daemon=True)
    th.start()
    return server, th


def stop_tg_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()

