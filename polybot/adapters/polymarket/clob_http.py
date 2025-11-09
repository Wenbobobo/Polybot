from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx


class ClobHttpClient:
    """Lightweight HTTP client for Polymarket CLOB endpoints.

    Endpoints (based on public docs):
      - GET /markets -> { data: [ { condition_id|id, question|title, ... } ], next_cursor? }
      - GET /markets/{condition_id} -> { question, tokens: [ { name|symbol, token_id|tokenId|id } ] }

    We keep the mapping tolerant to slight shape differences and envelopes.
    """

    def __init__(self, base_url: str, client: Optional[httpx.Client] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout)

    def get_simplified_markets(self, cursor: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = int(limit)
        r = self.client.get("/markets", params=params)
        r.raise_for_status()
        payload = r.json()
        # Normalize to { data: [...], next_cursor?: str }
        if isinstance(payload, list):
            return {"data": payload}
        if isinstance(payload, dict):
            out: Dict[str, Any] = {"data": payload.get("data") or []}
            nxt = payload.get("next_cursor") or payload.get("next")
            if nxt:
                out["next_cursor"] = nxt
            return out
        return {"data": []}

    def get_market(self, condition_id: str) -> Dict[str, Any]:
        r = self.client.get(f"/markets/{condition_id}")
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, dict):
            return payload
        return {"tokens": []}

    def get_price(self, token_id: str, side: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"token_id": token_id}
        if side:
            params["side"] = str(side).upper()
        r = self.client.get("/price", params=params)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {"data": data}

    def get_midpoint(self, token_id: str) -> Dict[str, Any]:
        r = self.client.get("/midpoint", params={"token_id": token_id})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {"data": data}

    def get_spread(self, token_id: str) -> Dict[str, Any]:
        r = self.client.get("/spread", params={"token_id": token_id})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {"data": data}
