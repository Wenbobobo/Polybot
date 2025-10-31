from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import websockets


@dataclass
class WSMessage:
    raw: dict


class OrderbookWSClient:
    """Minimal WebSocket client for receiving orderbook messages.

    This does not encode Polymarket-specific subscription semantics yet.
    It simply connects and yields JSON-decoded messages for tests and ingestion scaffolding.
    """

    def __init__(self, url: str, ping_interval: float = 20.0):
        self.url = url
        self.ping_interval = ping_interval
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    async def __aenter__(self) -> "OrderbookWSClient":
        self._ws = await websockets.connect(self.url, ping_interval=self.ping_interval)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def messages(self) -> AsyncIterator[WSMessage]:
        assert self._ws is not None
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

