from __future__ import annotations

from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path
import tomllib

from .runner import MarketSpec
from polybot.strategy.spread import SpreadParams


@dataclass
class ServiceConfig:
    db_url: str
    markets: List[MarketSpec]
    default_spread: SpreadParams


def _parse_spread(obj: dict | None) -> SpreadParams:
    obj = obj or {}
    return SpreadParams(
        tick_size=float(obj.get("tick_size", 0.01)),
        size=float(obj.get("size", 10.0)),
        edge=float(obj.get("edge", 0.02)),
        staleness_threshold_ms=int(obj.get("staleness_threshold_ms", 2000)),
        max_mid_jump=float(obj.get("max_mid_jump", 0.03)),
        min_requote_interval_ms=int(obj.get("min_requote_interval_ms", 300)),
        max_inventory=float(obj.get("max_inventory", 100.0)),
        rebalance_ratio=float(obj.get("rebalance_ratio", 0.5)),
    )


def load_service_config(path: str | Path) -> ServiceConfig:
    p = Path(path)
    data = tomllib.loads(Path(p).read_text(encoding="utf-8")) if False else tomllib.load(open(p, "rb"))
    svc = data.get("service", {})
    db_url = svc.get("db_url", ":memory:")
    default_spread = _parse_spread(svc.get("spread"))
    markets: List[MarketSpec] = []
    for m in data.get("market", []) or []:
        sp = _parse_spread(m.get("spread")) if m.get("spread") is not None else None
        markets.append(
            MarketSpec(
                market_id=str(m["market_id"]),
                outcome_yes_id=str(m.get("outcome_yes_id", "yes")),
                ws_url=str(m["ws_url"]),
                subscribe=bool(m.get("subscribe", True)),
                max_messages=int(m.get("max_messages", 0)) or None,
                spread_params=sp,
            )
        )
    return ServiceConfig(db_url=db_url, markets=markets, default_spread=default_spread)
