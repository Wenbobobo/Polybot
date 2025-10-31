from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass
class Config:
    polymarket_gamma_base_url: str
    polymarket_relayer_base_url: str
    signing_private_key: str
    db_url: str
    db_wal: bool
    ingestion_max_markets: int
    ingestion_snapshot_interval_ms: int
    ingestion_staleness_threshold_ms: int
    ingestion_ws_buffer_size: int
    ingestion_apply_batch_size: int
    strategy_dutch_book: bool
    strategy_spread_capture: bool
    strategy_conversions: bool
    strategy_news: bool
    thresholds_min_profit_usdc: float
    limits_max_per_market_usdc: float
    limits_max_open_orders: int
    logging_level: str
    logging_json: bool
    recordings_enable: bool
    recordings_path: str


def load_config(path: str | Path) -> Config:
    p = Path(path)
    with p.open("rb") as f:
        data = tomllib.load(f)

    pol = data.get("polymarket", {})
    sign = data.get("signing", {})
    db = data.get("db", {})
    ing = data.get("ingestion", {})
    strat = data.get("strategy", {})
    thr = data.get("thresholds", {})
    lim = data.get("limits", {})
    log = data.get("logging", {})
    rec = data.get("recordings", {})

    return Config(
        polymarket_gamma_base_url=str(pol.get("gamma_base_url", "")),
        polymarket_relayer_base_url=str(pol.get("relayer_base_url", "")),
        signing_private_key=str(sign.get("private_key", "")),
        db_url=str(db.get("url", "sqlite:///./polybot.db")),
        db_wal=bool(db.get("wal", True)),
        ingestion_max_markets=int(ing.get("max_markets", 100)),
        ingestion_snapshot_interval_ms=int(ing.get("snapshot_interval_ms", 30000)),
        ingestion_staleness_threshold_ms=int(ing.get("staleness_threshold_ms", 2000)),
        ingestion_ws_buffer_size=int(ing.get("ws_buffer_size", 8192)),
        ingestion_apply_batch_size=int(ing.get("apply_batch_size", 256)),
        strategy_dutch_book=bool(strat.get("dutch_book", True)),
        strategy_spread_capture=bool(strat.get("spread_capture", True)),
        strategy_conversions=bool(strat.get("conversions", False)),
        strategy_news=bool(strat.get("news", False)),
        thresholds_min_profit_usdc=float(thr.get("min_profit_usdc", 0.02)),
        limits_max_per_market_usdc=float(lim.get("max_per_market_usdc", 100.0)),
        limits_max_open_orders=int(lim.get("max_open_orders", 500)),
        logging_level=str(log.get("level", "INFO")),
        logging_json=bool(log.get("json", True)),
        recordings_enable=bool(rec.get("enable", True)),
        recordings_path=str(rec.get("path", "./recordings")),
    )


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config_stack(paths: list[str | Path]) -> Config:
    merged: dict = {}
    for p in paths:
        pth = Path(p)
        if not pth.exists():
            continue
        with pth.open("rb") as f:
            data = tomllib.load(f)
        merged = _deep_merge(merged, data)
    # reuse load_config by writing to a temp dict? Instead, adapt parsing here
    pol = merged.get("polymarket", {})
    sign = merged.get("signing", {})
    db = merged.get("db", {})
    ing = merged.get("ingestion", {})
    strat = merged.get("strategy", {})
    thr = merged.get("thresholds", {})
    lim = merged.get("limits", {})
    log = merged.get("logging", {})
    rec = merged.get("recordings", {})
    return Config(
        polymarket_gamma_base_url=str(pol.get("gamma_base_url", "")),
        polymarket_relayer_base_url=str(pol.get("relayer_base_url", "")),
        signing_private_key=str(sign.get("private_key", "")),
        db_url=str(db.get("url", "sqlite:///./polybot.db")),
        db_wal=bool(db.get("wal", True)),
        ingestion_max_markets=int(ing.get("max_markets", 100)),
        ingestion_snapshot_interval_ms=int(ing.get("snapshot_interval_ms", 30000)),
        ingestion_staleness_threshold_ms=int(ing.get("staleness_threshold_ms", 2000)),
        ingestion_ws_buffer_size=int(ing.get("ws_buffer_size", 8192)),
        ingestion_apply_batch_size=int(ing.get("apply_batch_size", 256)),
        strategy_dutch_book=bool(strat.get("dutch_book", True)),
        strategy_spread_capture=bool(strat.get("spread_capture", True)),
        strategy_conversions=bool(strat.get("conversions", False)),
        strategy_news=bool(strat.get("news", False)),
        thresholds_min_profit_usdc=float(thr.get("min_profit_usdc", 0.02)),
        limits_max_per_market_usdc=float(lim.get("max_per_market_usdc", 100.0)),
        limits_max_open_orders=int(lim.get("max_open_orders", 500)),
        logging_level=str(log.get("level", "INFO")),
        logging_json=bool(log.get("json", True)),
        recordings_enable=bool(rec.get("enable", True)),
        recordings_path=str(rec.get("path", "./recordings")),
    )
