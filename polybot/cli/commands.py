from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from polybot.storage.db import connect_sqlite, enable_wal, connect
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
from polybot.strategy.dutch_runner import DutchRunner, DutchSpec
from polybot.exec.engine import ExecutionEngine
from polybot.adapters.polymarket.relayer import FakeRelayer
from polybot.adapters.polymarket.relayer import build_relayer
from polybot.observability.health import check_staleness
from polybot.observability.metrics import list_counters, list_counters_labelled, get_counter_labelled
from polybot.observability.prometheus import export_text as prometheus_export_text
from polybot.service.config import load_service_config
from polybot.service.runner import ServiceRunner
from polybot.observability.recording import write_jsonl, read_jsonl
from polybot.observability.server import start_metrics_server
from polybot.storage.migrate import migrate as migrate_db
from polybot.tgbot.agent import BotAgent, BotContext
from polybot.tgbot.runner import TelegramUpdateRunner
from polybot.storage.db import parse_db_url
from polybot.adapters.polymarket.ctf import build_ctf, MergeRequest, SplitRequest


def init_db(db_url: str):
    con = connect(db_url)
    enable_wal(con)
    schema_mod.create_all(con)
    return con


def cmd_replay(file: str, market_id: str, db_url: str = ":memory:") -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    for event in read_jsonl(file):
        ing.process(event)


def cmd_status(db_url: str = ":memory:", verbose: bool = False) -> str:
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
        if verbose:
            qp = get_counter_labelled("quotes_placed", {"market": mkt})
            qc = get_counter_labelled("quotes_canceled", {"market": mkt})
            qs = get_counter_labelled("quotes_skipped", {"market": mkt})
            qss = get_counter_labelled("quotes_skipped_same", {"market": mkt})
            qrl = get_counter_labelled("quotes_rate_limited", {"market": mkt})
            qcrl = get_counter_labelled("quotes_cancel_rate_limited", {"market": mkt})
            op = get_counter_labelled("orders_placed", {"market": mkt})
            of = get_counter_labelled("orders_filled", {"market": mkt})
            rak_ok = get_counter_labelled("relayer_acks_accepted", {"market": mkt})
            rak_rej = get_counter_labelled("relayer_acks_rejected", {"market": mkt})
            eret = get_counter_labelled("engine_retries", {"market": mkt})
            dplaced = get_counter_labelled("dutch_orders_placed", {"market": mkt})
            drh = get_counter_labelled("dutch_rulehash_changed", {"market": mkt})
            ems = get_counter_labelled("engine_execute_plan_ms_sum", {"market": mkt})
            ec = get_counter_labelled("engine_execute_plan_count", {"market": mkt})
            avg_ms = (ems / ec) if ec else 0
            total_resyncs = gap + csum + firstd
            resync_ratio = (total_resyncs / max(1, applied)) if applied else 0
            lines.append(f"  quotes: placed={qp} canceled={qc} skipped={qs} skipped_same={qss} rate_limited={qrl} cancel_rate_limited={qcrl}")
            lines.append(f"  orders: placed={op} filled={of} exec_avg_ms={avg_ms:.1f} exec_count={ec} retries={eret}")
            lines.append(f"  relayer: acks_accepted={rak_ok} acks_rejected={rak_rej}")
            lines.append(f"  dutch: placed={dplaced} rulehash_changed={drh}")
            lines.append(f"  resyncs: total={total_resyncs} ratio={resync_ratio:.3f}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_status_top(db_url: str = ":memory:", limit: int = 5) -> str:
    """Show top markets by resync ratio and cancel rate-limit events.

    Uses counters accumulated in-process; intended for quick diagnostics.
    """
    con = connect_sqlite(db_url)
    rows = con.execute("SELECT market_id, last_seq, last_update_ts_ms, snapshots, deltas FROM market_status ORDER BY market_id").fetchall()
    stats = []
    for r in rows:
        mkt = r[0]
        applied = get_counter_labelled("ingestion_msg_applied", {"market": mkt})
        gap = get_counter_labelled("ingestion_resync_gap", {"market": mkt})
        csum = get_counter_labelled("ingestion_resync_checksum", {"market": mkt})
        firstd = get_counter_labelled("ingestion_resync_first_delta", {"market": mkt})
        total_resyncs = gap + csum + firstd
        resync_ratio = (total_resyncs / max(1, applied)) if applied else 0
        cancel_rl = get_counter_labelled("quotes_cancel_rate_limited", {"market": mkt})
        rejects = get_counter_labelled("relayer_acks_rejected", {"market": mkt})
        stats.append((mkt, resync_ratio, cancel_rl, rejects))
    # Sort: resync ratio desc, then rejects desc, then cancel rate-limit desc
    stats.sort(key=lambda x: (-x[1], -x[3], -x[2], x[0]))
    top = stats[: max(1, limit)]
    lines = ["market_id resync_ratio rejects cancel_rate_limited"]
    for mkt, ratio, crl, rej in top:
        lines.append(f"{mkt} {ratio:.3f} {rej} {crl}")
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


def cmd_metrics_export() -> str:
    """Return Prometheus text exposition format for in-process metrics."""
    text = prometheus_export_text()
    print(text, end="")
    return text


def cmd_migrate_timescale_print() -> str:
    """Print the optional Timescale migration SQL.

    This does not apply any changes; it simply prints the contents of
    migrations/postgres/010_timescale.sql if present.
    """
    p = Path("migrations/postgres/010_timescale.sql")
    if not p.exists():
        msg = "timescale migration file not found"
        print(msg)
        return msg
    text = p.read_text(encoding="utf-8")
    print(text, end="")
    return text


def cmd_preflight(config_path: str) -> str:
    """Validate a service config TOML before enabling real trading.

    Checks:
    - TOML parse success
    - DB URL scheme supported
    - If relayer.type == real: private_key format, chain_id > 0
    - At least one market configured
    Returns a multi-line string summary and prints it.
    """
    issues: list[str] = []
    try:
        cfg = load_service_config(config_path)
    except Exception as e:  # noqa: BLE001
        out = f"INVALID: failed to parse config: {e}"
        print(out)
        return out
    # DB URL
    try:
        scheme, _ = parse_db_url(cfg.db_url)
        if scheme not in ("sqlite", "postgresql"):
            issues.append(f"unsupported db scheme: {scheme}")
    except Exception as e:  # noqa: BLE001
        issues.append(f"invalid db_url: {e}")
    # Relayer
    if cfg.relayer_type.lower() == "real":
        from polybot.adapters.polymarket.crypto import is_valid_private_key

        if not cfg.relayer_private_key or not is_valid_private_key(cfg.relayer_private_key):
            issues.append("relayer.private_key is invalid (expect 0x-prefixed 32-byte hex)")
        if int(cfg.relayer_chain_id) <= 0:
            issues.append("relayer.chain_id must be > 0")
    # Markets
    if not cfg.markets:
        issues.append("no markets configured")

    if issues:
        header = "INVALID: preflight checks failed"
        lines = [header] + [f" - {i}" for i in issues]
        out = "\n".join(lines)
        print(out)
        return out
    out = "OK: preflight passed"
    print(out)
    return out


def cmd_conversions_merge(market_id: str, yes_id: str, no_id: str, size: float) -> str:
    ctf = build_ctf("fake")
    ack = ctf.merge(MergeRequest(market_id=market_id, outcome_yes_id=yes_id, outcome_no_id=no_id, size=size))
    out = f"merge accepted={ack.accepted} tx_id={ack.tx_id} reason={ack.reason or ''}"
    print(out)
    return out


def cmd_conversions_split(market_id: str, yes_id: str, no_id: str, usdc_amount: float) -> str:
    ctf = build_ctf("fake")
    ack = ctf.split(SplitRequest(market_id=market_id, outcome_yes_id=yes_id, outcome_no_id=no_id, usdc_amount=usdc_amount))
    out = f"split accepted={ack.accepted} tx_id={ack.tx_id} reason={ack.reason or ''}"
    print(out)
    return out


def cmd_smoke_live(config_path: str, market_id: str, outcome_id: str, side: str, price: float, size: float, base_url: str, private_key: str, chain_id: int = 137, timeout_s: float = 10.0) -> str:
    pre = cmd_preflight(config_path)
    if not pre.startswith("OK:"):
        return pre
    res = cmd_relayer_dry_run(market_id, outcome_id, side, price, size, base_url=base_url, private_key=private_key, db_url=":memory:", chain_id=chain_id, timeout_s=timeout_s)
    out = f"{pre}\n{res}"
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
    rel_kwargs = {
        "base_url": cfg.relayer_base_url,
        "dry_run": cfg.relayer_dry_run,
        "private_key": cfg.relayer_private_key,
        "chain_id": cfg.relayer_chain_id,
        "timeout_s": cfg.relayer_timeout_s,
    }
    sr = ServiceRunner(
        db_url=cfg.db_url,
        params=cfg.default_spread,
        relayer_type=cfg.relayer_type,
        relayer_kwargs=rel_kwargs,
        engine_max_retries=cfg.engine_max_retries,
        engine_retry_sleep_ms=cfg.engine_retry_sleep_ms,
    )
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


async def cmd_dutch_run_replay_async(
    file: str,
    market_id: str,
    outcomes_csv: str | None,
    db_url: str = ":memory:",
    min_profit_usdc: float = 0.02,
    default_size: float = 1.0,
    safety_margin_usdc: float = 0.0,
    fee_bps: float = 0.0,
    slippage_ticks: int = 0,
    allow_other: bool = False,
    verbose: bool = False,
) -> None:
    setup_logging()
    con = init_db(db_url)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    if outcomes_csv:
        outcomes = [o.strip() for o in outcomes_csv.split(",") if o.strip()]
    else:
        rows = con.execute("SELECT outcome_id FROM outcomes WHERE market_id=? ORDER BY outcome_id", (market_id,)).fetchall()
        outcomes = [r[0] for r in rows]
    if not outcomes:
        print(f"no outcomes found for market {market_id}; nothing to do")
        return
    spec = DutchSpec(market_id, outcomes)
    runner = DutchRunner(
        spec,
        engine,
        min_profit_usdc=min_profit_usdc,
        default_size=default_size,
        meta_db=con,
        safety_margin_usdc=safety_margin_usdc,
        fee_bps=fee_bps,
        slippage_ticks=slippage_ticks,
        allow_other=allow_other,
    )

    # Preload events to both run detection and compute final margin if verbose
    events = list(read_jsonl(file))

    # Compute diagnostic margins if requested
    if verbose:
        from polybot.adapters.polymarket.orderbook import OrderbookAssembler
        from polybot.strategy.dutch_book import MarketQuotes, OutcomeQuote, plan_dutch_book_with_safety as _plan
        from polybot.core.pricing import sum_prices
        assemblers = {oid: OrderbookAssembler(market_id) for oid in outcomes}
        for e in events:
            oid = e.get("outcome_id")
            if oid in assemblers:
                if e.get("type") == "snapshot":
                    assemblers[oid].apply_snapshot(e)
                elif e.get("type") == "delta":
                    assemblers[oid].apply_delta(e)
        outs: list[OutcomeQuote] = []
        for oid, asm in assemblers.items():
            ob = asm.apply_delta({"seq": asm._seq})
            ba = ob.best_ask()
            if not ba:
                continue
            # Pull metadata from DB when available
            row = con.execute("SELECT name, tick_size, min_size FROM outcomes WHERE outcome_id=?", (oid,)).fetchone()
            name, tick, mn = (row or (None, 0.01, 1.0))
            outs.append(OutcomeQuote(outcome_id=oid, best_ask=ba.price, tick_size=float(tick), min_size=float(mn), name=name))
        if outs:
            quotes = MarketQuotes(market_id=market_id, outcomes=outs)
            total_ask = sum_prices([o.best_ask for o in outs])
            margin = 1.0 - total_ask
            eff_plan = _plan(
                quotes,
                min_profit_usdc=min_profit_usdc,
                safety_margin_usdc=safety_margin_usdc,
                fee_bps=fee_bps,
                slippage_ticks=slippage_ticks,
                allow_other=allow_other,
                default_size=default_size,
            )
            print(f"diagnostic: total_ask={total_ask:.6f} margin={margin:.6f} plan={'yes' if eff_plan else 'no'}")

    async def _aiter():
        for e in events:
            yield e

    now_ms = lambda: int(time.time() * 1000)
    await runner.run(_aiter(), now_ms)


async def cmd_mock_ws_async(messages_file: Optional[str] = None, host: str = "127.0.0.1", port: int = 9000) -> None:
    import json
    import websockets
    msgs = None
    if messages_file:
        msgs = json.loads(Path(messages_file).read_text(encoding="utf-8"))
    else:
        msgs = [
            {"type": "l2_snapshot", "seq": 1, "bids": [[0.40, 100.0]], "asks": [[0.47, 100.0]]},
            {"type": "l2_update", "seq": 2},
            {"type": "l2_update", "seq": 3, "bids": [[0.41, 10.0]]},
        ]

    async def handler(websocket):
        try:
            # optional subscribe
            await asyncio.wait_for(websocket.recv(), timeout=0.2)
        except Exception:
            pass
        for m in msgs:
            await websocket.send(json.dumps(m))
        await asyncio.sleep(0.05)

    server = await websockets.serve(handler, host, port)
    print(f"mock-ws listening on ws://{host}:{port} and will close after sending {len(msgs)} messages")
    await asyncio.sleep(0.5)
    server.close()
    await server.wait_closed()


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


def cmd_metrics_serve(host: str = "127.0.0.1", port: int = 0) -> int:
    server, _ = start_metrics_server(host, port)
    actual_port = server.server_address[1]
    print(f"metrics-serve listening on http://{host}:{actual_port}/metrics")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
    return actual_port


def cmd_migrate(db_url: str, print_sql: bool = False, apply: bool = False) -> str:
    """Run or print DB migrations for the given URL.

    - SQLite: returns a summary (schema is applied by init_db in service/CLI).
    - PostgreSQL: prints SQL when print_sql=True; raises NotImplementedError otherwise.
    """
    out = migrate_db(db_url, print_sql_only=print_sql, apply=apply)
    if print_sql:
        print(out)
    else:
        print(str(out))
    return out


def cmd_relayer_dry_run(market_id: str, outcome_id: str, side: str, price: float, size: float, base_url: str, private_key: str, db_url: str = ":memory:", chain_id: int = 137, timeout_s: float = 10.0) -> str:
    """Place a single IOC order via 'real' relayer in dry-run mode.

    This uses build_relayer('real', base_url=..., private_key=..., dry_run=True).
    If the real client is unavailable, prints a helpful error.
    """
    setup_logging()
    try:
        rel = build_relayer("real", base_url=base_url, private_key=private_key, dry_run=True, chain_id=chain_id, timeout_s=timeout_s)
    except Exception as e:
        # If the relayer is unavailable and PK is clearly invalid, provide a clearer hint
        try:
            from polybot.adapters.polymarket.crypto import is_valid_private_key
            if not is_valid_private_key(private_key):
                msg = "invalid private_key: expecting 0x-prefixed 32-byte hex"
                print(msg)
                return msg
        except Exception:
            pass
        msg = f"relayer unavailable: {e}"
        print(msg)
        return msg
    from polybot.exec.planning import ExecutionPlan, OrderIntent
    con = init_db(db_url)
    from polybot.exec.engine import ExecutionEngine

    engine = ExecutionEngine(rel, audit_db=con)
    plan = ExecutionPlan(intents=[OrderIntent(market_id=market_id, outcome_id=outcome_id, side=side, price=price, size=size, tif="IOC")], expected_profit=0.0, rationale="dry_run")
    res = engine.execute_plan(plan)
    out = f"placed={len(res.acks)} accepted={sum(1 for a in res.acks if a.accepted)}"
    print(out)
    return out


def _try_build_real_relayer(base_url: str, private_key: str, chain_id: int = 137, timeout_s: float = 10.0):
    try:
        return build_relayer("real", base_url=base_url, private_key=private_key, dry_run=False, chain_id=chain_id, timeout_s=timeout_s)
    except Exception as e:  # noqa: BLE001
        return f"relayer unavailable: {e}"


def cmd_relayer_approve_usdc(base_url: str, private_key: str, amount: float, retries: int = 2, backoff_ms: int = 100, chain_id: int = 137, timeout_s: float = 10.0) -> str:
    """Approve USDC spend for relayer (stub).

    Until a real client is wired with allowance helpers, this prints a friendly message
    when the relayer is unavailable or lacks the method.
    """
    from polybot.observability.metrics import inc_labelled
    rel = _try_build_real_relayer(base_url, private_key, chain_id=chain_id, timeout_s=timeout_s)
    if isinstance(rel, str):
        print(rel)
        return rel
    attempt = 0
    while True:
        try:
            inc_labelled("relayer_allowance_attempts", {"kind": "usdc"}, 1)
            if hasattr(rel, "approve_usdc"):
                tx = rel.approve_usdc(amount)  # type: ignore[attr-defined]
                msg = f"approve_usdc submitted: {tx}"
            else:
                msg = "not implemented: relayer client missing approve_usdc()"
            print(msg)
            return msg
        except Exception as e:  # noqa: BLE001
            attempt += 1
            inc_labelled("relayer_allowance_errors", {"kind": "usdc"}, 1)
            if attempt > retries:
                msg = f"relayer unavailable: {e}"
                print(msg)
                return msg
            import time as _t
            _t.sleep(backoff_ms / 1000.0)


def cmd_relayer_approve_outcome(base_url: str, private_key: str, token_address: str, amount: float, retries: int = 2, backoff_ms: int = 100, chain_id: int = 137, timeout_s: float = 10.0) -> str:
    """Approve outcome token spend for relayer (stub)."""
    from polybot.observability.metrics import inc_labelled
    rel = _try_build_real_relayer(base_url, private_key, chain_id=chain_id, timeout_s=timeout_s)
    if isinstance(rel, str):
        print(rel)
        return rel
    attempt = 0
    while True:
        try:
            inc_labelled("relayer_allowance_attempts", {"kind": "outcome"}, 1)
            if hasattr(rel, "approve_outcome"):
                tx = rel.approve_outcome(token_address, amount)  # type: ignore[attr-defined]
                msg = f"approve_outcome submitted: {tx}"
            else:
                msg = "not implemented: relayer client missing approve_outcome()"
            print(msg)
            return msg
        except Exception as e:  # noqa: BLE001
            attempt += 1
            inc_labelled("relayer_allowance_errors", {"kind": "outcome"}, 1)
            if attempt > retries:
                msg = f"relayer unavailable: {e}"
                print(msg)
                return msg
            import time as _t
            _t.sleep(backoff_ms / 1000.0)


def cmd_tgbot_run_local(updates_file: str, market_id: str, outcome_yes_id: str, db_url: str = ":memory:") -> str:
    setup_logging()
    con = init_db(db_url)
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    agent = BotAgent(engine, BotContext(market_id=market_id, outcome_yes_id=outcome_yes_id))
    runner = TelegramUpdateRunner(agent)
    outputs: list[str] = []
    for e in read_jsonl(updates_file):
        outputs.append(runner.handle_update(e))
    out = "\n".join(outputs)
    print(out)
    return out
