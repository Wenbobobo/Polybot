from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


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
            market = {
                "market_id": str(m.get("id")),
                "title": str(m.get("title", "")),
                "status": str(m.get("status", "")),
                "outcomes": [
                    {
                        "outcome_id": str(o.get("id")),
                        "name": str(o.get("name", "")),
                    }
                    for o in m.get("outcomes", [])
                ],
            }
            normalized.append(market)
        return normalized

