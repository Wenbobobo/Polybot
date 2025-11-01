from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Any, Dict

import websockets


@dataclass
class WSMessage:
    raw: dict


class OrderbookWSClient:
    """Minimal WebSocket client for receiving orderbook messages.

    This does not encode Polymarket-specific subscription semantics yet.
    It simply connects and yields JSON-decoded messages for tests and ingestion scaffolding.
    """

    def __init__(self, url: str, ping_interval: float = 20.0, subscribe_message: Optional[Dict[str, Any]] = None, max_reconnects: int = 0, backoff_ms: int = 100):
        self.url = url
        self.ping_interval = ping_interval
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._subscribe_message = subscribe_message
        self._max_reconnects = max(0, int(max_reconnects))
        self._backoff_ms = max(0, int(backoff_ms))

    async def __aenter__(self) -> "OrderbookWSClient":
        self._ws = await websockets.connect(self.url, ping_interval=self.ping_interval)
        if self._subscribe_message is not None:
            await self._ws.send(json.dumps(self._subscribe_message))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def messages(self) -> AsyncIterator[WSMessage]:
        assert self._ws is not None
        attempts = 0
        while True:
            try:
                async for msg in self._ws:
                    if isinstance(msg, (bytes, bytearray)):
                        try:
                            payload = json.loads(msg.decode("utf-8"))
                        except Exception:
                            continue
                    else:
                        try:
                            payload = json.loads(msg)
                        except Exception:
                            continue
                    yield WSMessage(raw=payload)
                # Normal closure; stop unless we are allowed to reconnect
                if attempts >= self._max_reconnects:
                    break
                attempts += 1
                await self._reconnect(attempts)
                continue
            except Exception:
                if attempts >= self._max_reconnects:
                    break
                attempts += 1
                await self._reconnect(attempts)
                continue

    async def _reconnect(self, attempts: int) -> None:
        try:
            if self._ws:
                await self._ws.close()
        except Exception:
            pass
        # backoff
        try:
            await asyncio.sleep((self._backoff_ms * attempts) / 1000.0)
        except Exception:
            pass
        # reconnect and re-subscribe
        self._ws = await websockets.connect(self.url, ping_interval=self.ping_interval)
        if self._subscribe_message is not None and self._ws is not None:
            try:
                await self._ws.send(json.dumps(self._subscribe_message))
            except Exception:
                pass
