from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from polybot.storage.db import connect_sqlite, enable_wal
from polybot.storage import schema as schema_mod
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.observability.recording import read_jsonl
from polybot.observability.logging import setup_logging
from polybot.ingestion.runner import run_orderbook_stream
from polybot.ingestion.snapshot import SnapshotProvider, FakeSnapshotProvider
from polybot.adapters.polymarket.ws import OrderbookWSClient
from polybot.ingestion.markets import refresh_markets
from polybot.adapters.polymarket.gamma_http import GammaHttpClient
import httpx
import time
from polybot.adapters.polymarket.ws_translator import translate_polymarket_message
from polybot.strategy.spread import SpreadParams
from polybot.strategy.spread_quoter import SpreadQuoter
from polybot.strategy.quoter_runner import QuoterRunner
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.observability.health import check_staleness
from polybot.observability.metrics import list_counters, list_counters_labelled, get_counter_labelled
from polybot.service.config import load_service_config
from polybot.service.runner import ServiceRunner
from polybot.observability.recording import write_jsonl, read_jsonl


def init_db(db_url: str):
    con = connect_sqlite(db_url)
    enable_wal(con)
    schema_mod.create_all(con)
    return con


def cmd_replay(file: str, market_id: str, db_url: str = ":memory:") -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    for event in read_jsonl(file):
        ing.process(event)


def cmd_status(db_url: str = ":memory:") -> str:
    """Return a human-readable status summary string for markets in DB."""
    con = connect_sqlite(db_url)
    rows = con.execute(
        "SELECT market_id, last_seq, last_update_ts_ms, snapshots, deltas FROM market_status ORDER BY market_id"
    ).fetchall()
    if not rows:
        return "No market status available."
    lines = ["market_id last_seq last_update_ms snapshots deltas applied invalid resync_gap resync_checksum resync_first_delta"]
    for r in rows:
        mkt = r[0]
        applied = get_counter_labelled("ingestion_msg_applied", {"market": mkt})
        invalid = get_counter_labelled("ingestion_msg_invalid", {"market": mkt})
        gap = get_counter_labelled("ingestion_resync_gap", {"market": mkt})
        csum = get_counter_labelled("ingestion_resync_checksum", {"market": mkt})
        firstd = get_counter_labelled("ingestion_resync_first_delta", {"market": mkt})
        lines.append(f"{mkt} {r[1]} {r[2]} {r[3]} {r[4]} {applied} {invalid} {gap} {csum} {firstd}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_status_watch(db_url: str = ":memory:", interval_ms: int = 1000, iterations: int = 5) -> str:
    import time
    outputs: list[str] = []
    for _ in range(max(1, iterations)):
        out = cmd_status(db_url=db_url)
        outputs.append(out)
        time.sleep(max(0, interval_ms) / 1000.0)
    return "\n---\n".join(outputs)


def cmd_health(db_url: str = ":memory:", staleness_threshold_ms: int = 30000) -> str:
    con = connect_sqlite(db_url)
    issues = check_staleness(con, staleness_threshold_ms)
    if not issues:
        out = "OK: no stale markets"
        print(out)
        return out
    lines = ["STALE markets:"]
    for i in issues:
        lines.append(f"{i['market_id']} age_ms={i['age_ms']}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_metrics() -> str:
    parts = ["counters:"]
    for name, val in list_counters():
        parts.append(f"{name} {val}")
    parts.append("labelled:")
    for name, labels, val in list_counters_labelled():
        label_str = ",".join([f"{k}={v}" for k, v in labels])
        parts.append(f"{name}{{{label_str}}} {val}")
    out = "\n".join(parts)
    print(out)
    return out


def cmd_refresh_markets(base_url: str, db_url: str = ":memory:") -> int:
    setup_logging()
    con = init_db(db_url)
    client = httpx.Client(base_url=base_url, timeout=10.0)
    ghc = GammaHttpClient(base_url=base_url, client=client)
    n = refresh_markets(con, ghc)
    print(f"refreshed_markets={n}")
    return n


def cmd_refresh_markets_with_client(httpx_client: httpx.Client, base_url: str, db_url: str = ":memory:") -> int:
    con = init_db(db_url)
    ghc = GammaHttpClient(base_url=base_url, client=httpx_client)
    return refresh_markets(con, ghc)


async def _aiter_translated_ws(url: str, max_messages: Optional[int] = None, subscribe_message: Optional[dict] = None):
    count = 0
    async with OrderbookWSClient(url, subscribe_message=subscribe_message) as client:
        async for m in client.messages():
            out = translate_polymarket_message(m.raw)
            if out is None:
                continue
            yield out
            count += 1
            if max_messages is not None and count >= max_messages:
                break


async def cmd_quoter_run_ws_async(
    url: str,
    market_id: str,
    outcome_yes_id: str,
    db_url: str = ":memory:",
    max_messages: Optional[int] = None,
    params: Optional[SpreadParams] = None,
    subscribe: bool = False,
) -> None:
    setup_logging()
    con = init_db(db_url)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = params or SpreadParams()
    quoter = SpreadQuoter(market_id, outcome_yes_id, params, engine)
    runner = QuoterRunner(market_id, quoter)
    now_ms = lambda: int(time.time() * 1000)
    sub = None
    if subscribe:
        from polybot.adapters.polymarket.subscribe import build_subscribe_l2

        sub = build_subscribe_l2(market_id)
    await runner.run(_aiter_translated_ws(url, max_messages, subscribe_message=sub), now_ms)


async def cmd_run_service_from_config_async(config_path: str) -> None:
    cfg = load_service_config(config_path)
    sr = ServiceRunner(db_url=cfg.db_url, params=cfg.default_spread)
    await sr.run_markets(cfg.markets)


async def cmd_record_ws_async(url: str, outfile: str, max_messages: Optional[int] = None, subscribe: bool = False, translate: bool = True) -> None:
    setup_logging()
    sub = None
    if subscribe:
        from polybot.adapters.polymarket.subscribe import build_subscribe_l2

        sub = build_subscribe_l2("*")
    events = []
    count = 0
    async with OrderbookWSClient(url, subscribe_message=sub) as client:
        async for m in client.messages():
            data = m.raw
            if translate:
                data = translate_polymarket_message(data)
            if data is None:
                continue
            events.append(data)
            count += 1
            if max_messages is not None and count >= max_messages:
                break
    write_jsonl(outfile, events)


async def cmd_quoter_run_replay_async(file: str, market_id: str, outcome_yes_id: str, db_url: str = ":memory:", params: Optional[SpreadParams] = None) -> None:
    setup_logging()
    con = init_db(db_url)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    params = params or SpreadParams()
    quoter = SpreadQuoter(market_id, outcome_yes_id, params, engine)
    runner = QuoterRunner(market_id, quoter)

    async def _aiter():
        for e in read_jsonl(file):
            yield e

    now_ms = lambda: int(time.time() * 1000)
    await runner.run(_aiter(), now_ms)


async def _aiter_from_ws(url: str, max_messages: Optional[int] = None):
    count = 0
    async with OrderbookWSClient(url) as client:
        async for m in client.messages():
            yield m.raw
            count += 1
            if max_messages is not None and count >= max_messages:
                break


async def cmd_ingest_ws_async(url: str, market_id: str, snapshot_json: Optional[str] = None, db_url: str = ":memory:", max_messages: Optional[int] = None) -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    provider: SnapshotProvider
    if snapshot_json:
        import json

        snap = json.loads(Path(snapshot_json).read_text(encoding="utf-8"))
        provider = FakeSnapshotProvider(snap)
    else:
        provider = FakeSnapshotProvider({"type": "snapshot", "seq": 0, "bids": [], "asks": []})

    await run_orderbook_stream(market_id, _aiter_from_ws(url, max_messages=max_messages), ing, provider)


def cmd_ingest_ws(url: str, market_id: str, snapshot_json: Optional[str] = None, db_url: str = ":memory:", max_messages: Optional[int] = None) -> None:
    asyncio.run(cmd_ingest_ws_async(url, market_id, snapshot_json=snapshot_json, db_url=db_url, max_messages=max_messages))
