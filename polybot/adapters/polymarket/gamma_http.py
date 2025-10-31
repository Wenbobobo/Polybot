from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional

from .gamma import GammaClient


class GammaHttpClient:
    def __init__(self, base_url: str, client: Optional[httpx.Client] = None):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(base_url=self.base_url, timeout=10.0)

    def list_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets with basic pagination support.

        Accepts either a plain array payload or a paginated envelope:
        {"data": [...], "next": "cursor"}
        """
        out: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            path = "/markets"
            if cursor:
                path += f"?cursor={cursor}"
            resp = self.client.get(path)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                out.extend(payload)
                break
            if isinstance(payload, dict):
                out.extend(payload.get("data", []))
                cursor = payload.get("next") or None
                if not cursor:
                    break
            else:
                break
        return GammaClient.normalize_markets(out)
