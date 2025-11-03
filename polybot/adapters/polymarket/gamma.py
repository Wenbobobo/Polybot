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
            # Prefer explicit outcomes; otherwise derive from tokens
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
                    oid = o.get("id") or o.get("outcome_id") or o.get("token") or o.get("token_id") or o.get("tokenId")
                    name = o.get("name") or o.get("title") or o.get("displayName") or o.get("symbol") or ""
                    outs_norm.append({
                        "outcome_id": str(oid) if oid is not None else "",
                        "name": str(name),
                    })
                elif isinstance(o, str):
                    outs_norm.append({"outcome_id": o, "name": ""})
                else:
                    # Unknown shape; skip
                    continue
            # If no outcomes found, attempt to derive from tokens
            if not outs_norm:
                tokens = m.get("tokens") or []
                if isinstance(tokens, list):
                    for t in tokens:
                        if not isinstance(t, dict):
                            continue
                        oid = t.get("token_id") or t.get("tokenId") or t.get("id")
                        name = t.get("name") or t.get("symbol") or t.get("displayName") or ""
                        outs_norm.append({"outcome_id": str(oid) if oid is not None else "", "name": str(name)})
            # If outcomes exist but outcome_ids are empty and clobTokenIds present, zip map
            if outs_norm and not any(o.get("outcome_id") for o in outs_norm):
                cti = m.get("clobTokenIds")
                if isinstance(cti, str) and cti.strip():
                    tokens_list = [x.strip() for x in cti.split(",") if x.strip()]
                    if len(tokens_list) == len(outs_norm):
                        for i, tok in enumerate(tokens_list):
                            outs_norm[i]["outcome_id"] = tok
            # Map market identifiers and title/status variants
            market_id = m.get("condition_id") or m.get("id") or m.get("market_id") or m.get("market")
            title = m.get("title") or m.get("question") or m.get("name") or m.get("slug") or ""
            status = m.get("status")
            if status is None and "active" in m:
                status = "active" if m.get("active") else "inactive"
            market = {
                "market_id": str(market_id) if market_id is not None else "",
                "title": str(title),
                "status": str(status or ""),
                "outcomes": outs_norm,
            }
            normalized.append(market)
        return normalized
