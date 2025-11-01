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
    relayer_type: str = "fake"
    relayer_base_url: str = "https://clob.polymarket.com"
    relayer_dry_run: bool = True
    relayer_private_key: str = ""
    relayer_chain_id: int = 137
    relayer_timeout_s: float = 10.0


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
    data = tomllib.load(open(p, "rb"))
    # Optional secrets overlay from a sibling secrets.local.toml (gitignored by default)
    secrets_path = p.parent / "secrets.local.toml"
    if secrets_path.exists():
        try:
            secrets = tomllib.load(open(secrets_path, "rb"))
            # shallow merge only for [relayer]
            rel_overlay = (secrets.get("relayer", {}) or {})
            if rel_overlay:
                base_rel = (data.get("relayer", {}) or {}).copy()
                base_rel.update(rel_overlay)
                data["relayer"] = base_rel
        except Exception:
            pass
    svc = data.get("service", {})
    db_url = svc.get("db_url", ":memory:")
    rel = (data.get("relayer", {}) or {})
    relayer_type = rel.get("type", "fake")
    relayer_base_url = rel.get("base_url", "https://clob.polymarket.com")
    relayer_dry_run = bool(rel.get("dry_run", True))
    relayer_private_key = rel.get("private_key", "")
    relayer_chain_id = int(rel.get("chain_id", 137))
    relayer_timeout_s = float(rel.get("timeout_s", 10.0))
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
    return ServiceConfig(
        db_url=db_url,
        markets=markets,
        default_spread=default_spread,
        relayer_type=relayer_type,
        relayer_base_url=str(relayer_base_url),
        relayer_dry_run=relayer_dry_run,
        relayer_private_key=str(relayer_private_key),
        relayer_chain_id=relayer_chain_id,
        relayer_timeout_s=relayer_timeout_s,
    )
