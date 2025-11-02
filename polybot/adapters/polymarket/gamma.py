from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import json as _json


@dataclass
class RawMarket:
    id: str
    title: str
    status: str
    outcomes: List[Dict[str, Any]]


class GammaClient:
    """Placeholder interface for Polymarket Gamma API.

    In tests, we will feed fixture data into normalize_markets without real HTTP.
    """

    @staticmethod
    def normalize_markets(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize a subset of market fields for internal models.

        Expects a list of dicts with minimal keys: id, title, status, outcomes(list of {id,name}).
        Returns a list of normalized dicts.
        """
        normalized: List[Dict[str, Any]] = []
        for m in raw:
            outs_norm: List[Dict[str, Any]] = []
            raw_outs = m.get("outcomes", [])
            # If outcomes is a JSON-encoded string, parse it
            if isinstance(raw_outs, str):
                try:
                    parsed = _json.loads(raw_outs)
                    raw_outs = parsed
                except Exception:
                    # treat as a single outcome id string
                    raw_outs = [raw_outs]
            for o in (raw_outs or []):
                if isinstance(o, dict):
                    oid = o.get("id") or o.get("outcome_id") or o.get("token")
                    name = o.get("name") or o.get("title") or o.get("displayName") or ""
                    outs_norm.append({
                        "outcome_id": str(oid) if oid is not None else "",
                        "name": str(name),
                    })
                elif isinstance(o, str):
                    outs_norm.append({"outcome_id": o, "name": ""})
                else:
                    # Unknown shape; skip
                    continue
            market = {
                "market_id": str(m.get("id")),
                "title": str(m.get("title", "")),
                "status": str(m.get("status", "")),
                "outcomes": outs_norm,
            }
            normalized.append(market)
        return normalized
