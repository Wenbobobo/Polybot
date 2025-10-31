from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional

from .gamma import GammaClient


class GammaHttpClient:
    def __init__(self, base_url: str, client: Optional[httpx.Client] = None):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(base_url=self.base_url, timeout=10.0)

    def list_markets(self) -> List[Dict[str, Any]]:
        # Endpoint path to be aligned with Polymarket Gamma; using placeholder "/markets".
        resp = self.client.get("/markets")
        resp.raise_for_status()
        data = resp.json()
        # Normalize to internal format using GammaClient utility
        return GammaClient.normalize_markets(data)

