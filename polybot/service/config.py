from __future__ import annotations

from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path
import tomllib

from .runner import MarketSpec


@dataclass
class ServiceConfig:
    db_url: str
    markets: List[MarketSpec]


def load_service_config(path: str | Path) -> ServiceConfig:
    p = Path(path)
    data = tomllib.loads(Path(p).read_text(encoding="utf-8")) if False else tomllib.load(open(p, "rb"))
    svc = data.get("service", {})
    db_url = svc.get("db_url", ":memory:")
    markets: List[MarketSpec] = []
    for m in data.get("market", []) or []:
        markets.append(
            MarketSpec(
                market_id=str(m["market_id"]),
                outcome_yes_id=str(m.get("outcome_yes_id", "yes")),
                ws_url=str(m["ws_url"]),
                subscribe=bool(m.get("subscribe", True)),
                max_messages=int(m.get("max_messages", 0)) or None,
            )
        )
    return ServiceConfig(db_url=db_url, markets=markets)

