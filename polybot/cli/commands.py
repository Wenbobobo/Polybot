from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
from types import SimpleNamespace

from polybot.storage.db import connect_sqlite, enable_wal, connect
from polybot.storage import schema as schema_mod
from polybot.ingestion.orderbook import OrderbookIngestor
from polybot.observability.recording import read_jsonl
from polybot.observability.logging import setup_logging
from polybot.ingestion.runner import run_orderbook_stream
from polybot.ingestion.snapshot import SnapshotProvider, FakeSnapshotProvider
from polybot.adapters.polymarket.ws import OrderbookWSClient
from polybot.ingestion.markets import refresh_markets
from polybot.ingestion.market_sync import sync_markets
from polybot.adapters.polymarket.clob_http import ClobHttpClient
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
from polybot.tgbot.webhook_server import start_tg_server, stop_tg_server
from polybot.storage.db import parse_db_url
from polybot.adapters.polymarket.ctf import build_ctf, MergeRequest, SplitRequest
from polybot.observability.metrics import reset as metrics_reset_fn
import json as _json
from polybot.adapters.polymarket.market_resolver import (
    PyClobMarketSearcher,
    parse_polymarket_url,
    choose_outcome,
    OutcomeInfo,
)
from polybot.adapters.polymarket.clob_http import ClobHttpClient
try:  # optional import for tests/real usage
    from polybot.adapters.polymarket.real_client import make_pyclob_client as _make_pyclob_client  # type: ignore
except Exception:  # pragma: no cover
    _make_pyclob_client = None


def init_db(db_url: str):
    con = connect(db_url)
    enable_wal(con)
    schema_mod.create_all(con)
    return con


def _builder_kwargs_from_env() -> Dict[str, str]:
    env = os.environ
    out: Dict[str, str] = {}
    api_key = env.get("POLY_BUILDER_API_KEY")
    api_secret = env.get("POLY_BUILDER_SECRET")
    api_passphrase = env.get("POLY_BUILDER_PASSPHRASE")
    if api_key and api_secret and api_passphrase:
        out["builder_api_key"] = api_key
        out["builder_api_secret"] = api_secret
        out["builder_api_passphrase"] = api_passphrase
    remote_url = env.get("POLY_BUILDER_REMOTE_URL")
    if remote_url:
        out["builder_remote_url"] = remote_url
        token = env.get("POLY_BUILDER_TOKEN")
        if token:
            out["builder_remote_token"] = token
    return out


def _builder_kwargs_from_cfg(cfg) -> Dict[str, str]:
    out: Dict[str, str] = {}
    builder = getattr(cfg, "relayer_builder", None)
    if not builder:
        return out
    if builder.api_key and builder.api_secret and builder.api_passphrase:
        out["builder_api_key"] = builder.api_key
        out["builder_api_secret"] = builder.api_secret
        out["builder_api_passphrase"] = builder.api_passphrase
    if builder.url:
        out["builder_remote_url"] = builder.url
        if builder.token:
            out["builder_remote_token"] = builder.token
    return out


def _has_local_builder(kwargs: Dict[str, str]) -> bool:
    return all(kwargs.get(key) for key in ("builder_api_key", "builder_api_secret", "builder_api_passphrase"))


def _has_remote_builder(kwargs: Dict[str, str]) -> bool:
    return bool(kwargs.get("builder_remote_url"))


def _builder_source(kwargs: Dict[str, str]) -> str | None:
    if _has_local_builder(kwargs):
        return "local"
    if _has_remote_builder(kwargs):
        return "remote"
    return None


def _ensure_builder_ready(cfg, builder_kwargs: Dict[str, str]) -> tuple[bool, str | None]:
    if str(getattr(cfg, "relayer_type", "") or "").lower() != "real":
        return True, None
    if _builder_source(builder_kwargs):
        return True, None
    return False, "relayer.type=real requires builder credentials (api_key/api_secret/api_passphrase or remote url/token)"


def _collect_builder_kwargs(cfg) -> Dict[str, str]:
    builder_kwargs = _builder_kwargs_from_cfg(cfg)
    env_builder = _builder_kwargs_from_env()
    builder_kwargs.update(env_builder)
    return builder_kwargs


def _safe_json_dump(value: Any) -> str:
    try:
        import json as _json

        return _json.dumps(value, separators=(",", ":"), sort_keys=True)
    except Exception:
        return str(value)


def _resolve_markets_raw(
    *,
    url: str | None = None,
    query: str | None = None,
    prefer: str | None = None,
    use_pyclob: bool = True,
    base_url: str = "https://clob.polymarket.com",
    chain_id: int = 137,
    timeout_s: float = 10.0,
    http_timeout_s: float | None = None,
    http_page_scans: int = 2,
    debug: bool = False,
) -> tuple[list[dict], dict]:
    results: list[dict] = []
    dbg: dict[str, object] = {}
    if use_pyclob and _make_pyclob_client is None:
        try:
            from polybot.adapters.polymarket.real_client import make_pyclob_client as _reimp  # type: ignore

            globals()["_make_pyclob_client"] = _reimp
            if debug:
                dbg["pyclob_import"] = "ok"
        except Exception:
            if debug:
                dbg["pyclob_import"] = "import_failed"
            pass
    if use_pyclob and _make_pyclob_client is not None:
        try:
            client = _make_pyclob_client(base_url=base_url, private_key="", dry_run=True, chain_id=chain_id, timeout_s=timeout_s)
            searcher = PyClobMarketSearcher(client)
            used_fallback = False
            if url:
                infos = searcher.search_by_url(url, limit=5)
                if not infos:
                    meta = parse_polymarket_url(url)
                    slug = (meta.get("slug") or "")
                    if slug:
                        short = slug.split("/")[-1].replace("-", " ")
                        infos = searcher.search_by_query(short, limit=5)
                        used_fallback = True
            elif query:
                infos = searcher.search_by_query(query, limit=5)
            else:
                infos = []
            attempted_ids: list[str] = []
            if debug:
                dbg["search"] = {
                    "mode": "url" if url else ("query" if query else "none"),
                    "used_fallback_on_slug": used_fallback,
                    "results_count": len(infos),
                }
            for mi in infos:
                try:
                    sel = choose_outcome(mi.outcomes, prefer=prefer)
                    results.append(
                        {
                            "market_id": mi.market_id,
                            "title": mi.title,
                            "outcomes": [{"outcome_id": o.outcome_id, "name": o.name} for o in mi.outcomes],
                            "selected_outcome_id": sel.outcome_id if sel else None,
                            "selected_outcome_name": sel.name if sel else None,
                        }
                    )
                    attempted_ids.append(mi.market_id)
                except Exception:
                    attempted_ids.append(getattr(mi, "market_id", ""))
                    continue
            if debug:
                dbg["attempted_ids"] = attempted_ids
        except Exception as e:
            if debug:
                dbg["client_ctor_error"] = str(e)
            pass
    slug_for_url: str | None = None
    if url:
        parsed = parse_polymarket_url(url)
        slug_for_url = (parsed.get("slug") or "").lower()
    if not results:
        try:
            http = ClobHttpClient(base_url=base_url, timeout=(http_timeout_s or timeout_s))
            payload = http.get_simplified_markets(limit=100)
            data = payload.get("data") or []
            cursor = payload.get("next_cursor")
            needle = ""
            if url:
                meta = parse_polymarket_url(url)
                slug = (meta.get("slug") or "").split("/")[-1]
                needle = slug.replace("-", " ").lower()
            elif query:
                needle = query.lower()
            matches = []
            scans = 0
            for m in data:
                q = str(m.get("question") or m.get("title") or m.get("slug") or "").lower()
                if needle and needle in q:
                    matches.append(m)
            while not matches and cursor and scans < http_page_scans:
                nxt = http.get_simplified_markets(cursor=cursor, limit=100)
                data2 = nxt.get("data") or []
                for m in data2:
                    q = str(m.get("question") or m.get("title") or m.get("slug") or "").lower()
                    if needle and needle in q:
                        matches.append(m)
                cursor = nxt.get("next_cursor")
                scans += 1
            for m in matches[:5]:
                cond = str(m.get("condition_id") or m.get("id") or "").strip()
                title = str(m.get("question") or m.get("title") or "")
                outs = []
                names = m.get("outcomes") if isinstance(m.get("outcomes"), list) else []
                cti = m.get("clobTokenIds") if isinstance(m.get("clobTokenIds"), str) else ""
                tokens_list = [x.strip() for x in cti.split(",") if x.strip()] if cti else []
                if names and tokens_list and len(names) == len(tokens_list):
                    for i, name in enumerate(names):
                        outs.append({"outcome_id": tokens_list[i], "name": name})
                else:
                    for name in (names or []):
                        outs.append({"outcome_id": "", "name": name})
                sel_id = outs[0]["outcome_id"] if outs and outs[0]["outcome_id"] else None
                sel_name = outs[0]["name"] if outs else None
                results.append(
                    {
                        "market_id": cond,
                        "title": title,
                        "outcomes": outs,
                        "selected_outcome_id": sel_id,
                        "selected_outcome_name": sel_name,
                    }
                )
            if debug:
                dbg["http_fallback"] = {"matches": len(matches)}
        except Exception as e:
            if debug:
                dbg["http_fallback_error"] = str(e)
    if not results and url:
        next_payload = _resolve_market_via_next_data(url, timeout_s=http_timeout_s or timeout_s)
        if next_payload:
            outs = next_payload.get("outcomes") or []
            sel = None
            try:
                sel = choose_outcome(
                    [OutcomeInfo(outcome_id=o["outcome_id"], name=o["name"]) for o in outs],
                    prefer=prefer,
                )
            except Exception:
                sel = None
            sel_id = sel.outcome_id if sel else (outs[0]["outcome_id"] if outs else None)
            sel_name = sel.name if sel else (outs[0]["name"] if outs else None)
            results.append(
                {
                    "market_id": next_payload.get("market_id"),
                    "title": next_payload.get("title"),
                    "outcomes": outs,
                    "selected_outcome_id": sel_id,
                    "selected_outcome_name": sel_name,
                }
            )
            if debug:
                dbg["next_data"] = {"used": True}
        elif debug:
            dbg["next_data"] = {"used": False}
    if results and slug_for_url:
        segments = [seg.replace("-", " ").strip().lower() for seg in slug_for_url.split("/") if seg]
        def _matches(entry: dict) -> bool:
            title = str(entry.get("title") or "").lower()
            market_id = str(entry.get("market_id") or "").lower()
            return any(seg in title or seg in market_id for seg in segments)
        if segments and not any(_matches(r) for r in results):
            results.clear()
    return results, dbg


def _resolve_market_choice(
    *,
    url: str | None = None,
    query: str | None = None,
    prefer: str | None = None,
    base_url: str = "https://clob.polymarket.com",
    chain_id: int = 137,
    timeout_s: float = 10.0,
) -> dict | None:
    results, _ = _resolve_markets_raw(
        url=url,
        query=query,
        prefer=prefer,
        use_pyclob=True,
        base_url=base_url,
        chain_id=chain_id,
        timeout_s=timeout_s,
        http_page_scans=5,
    )
    if not results:
        return None
    entry = results[0]
    mid = entry.get("market_id")
    oid = entry.get("selected_outcome_id")
    if not mid or not oid:
        return None
    return entry


def cmd_replay(file: str, market_id: str, db_url: str = ":memory:") -> None:
    setup_logging()
    con = init_db(db_url)
    ing = OrderbookIngestor(con, market_id)
    for event in read_jsonl(file):
        ing.process(event)


def cmd_markets_list(db_url: str = ":memory:", limit: int = 10, as_json: bool = False) -> str:
    """List markets and their outcomes from DB, newest first by last_update.

    For convenience when picking a live smoke-test target after a Gamma refresh.
    """
    con = connect_sqlite(db_url)
    # Fall back to ORDER BY market_id if market_status missing rows
    rows = con.execute(
        "SELECT m.market_id, m.title, m.status, COALESCE(s.last_update_ts_ms, 0) as updated "
        "FROM markets m LEFT JOIN market_status s ON m.market_id = s.market_id "
        "ORDER BY updated DESC, m.market_id LIMIT ?",
        (max(1, int(limit)),),
    ).fetchall()
    items = []
    for mid, title, status, updated in rows:
        outs = con.execute(
            "SELECT outcome_id, name, tick_size, min_size FROM outcomes WHERE market_id = ? ORDER BY outcome_id",
            (mid,),
        ).fetchall()
        items.append(
            {
                "market_id": mid,
                "title": title,
                "status": status,
                "last_update_ts_ms": int(updated or 0),
                "outcomes": [
                    {
                        "outcome_id": o[0],
                        "name": o[1],
                        "tick_size": float(o[2] or 0.0),
                        "min_size": float(o[3] or 0.0),
                    }
                    for o in outs
                ],
            }
        )
    if as_json:
        out = _json.dumps(items)
        print(out)
        return out
    lines = ["market_id title status last_update_ms outcomes"]
    for it in items:
        lines.append(f"{it['market_id']} {it['title']} {it['status']} {it['last_update_ts_ms']} {len(it['outcomes'])}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_status(db_url: str = ":memory:", verbose: bool = False, as_json: bool = False) -> str:
    """Return a human-readable status summary string for markets in DB."""
    con = connect_sqlite(db_url)
    rows = con.execute(
        "SELECT market_id, last_seq, last_update_ts_ms, snapshots, deltas FROM market_status ORDER BY market_id"
    ).fetchall()
    if not rows:
        out = "No market status available."
        print(out)
        return out
    if as_json:
        import json as _json
        items = []
        for r in rows:
            mkt = r[0]
            applied = get_counter_labelled("ingestion_msg_applied", {"market": mkt})
            invalid = get_counter_labelled("ingestion_msg_invalid", {"market": mkt})
            gap = get_counter_labelled("ingestion_resync_gap", {"market": mkt})
            csum = get_counter_labelled("ingestion_resync_checksum", {"market": mkt})
            firstd = get_counter_labelled("ingestion_resync_first_delta", {"market": mkt})
            item = {
                "market_id": mkt,
                "last_seq": r[1],
                "last_update_ts_ms": r[2],
                "snapshots": r[3],
                "deltas": r[4],
                "applied": applied,
                "invalid": invalid,
                "resync_gap": gap,
                "resync_checksum": csum,
                "resync_first_delta": firstd,
            }
            if verbose:
                item["quotes_placed"] = get_counter_labelled("quotes_placed", {"market": mkt})
                item["quotes_cancel_rate_limited"] = get_counter_labelled("quotes_cancel_rate_limited", {"market": mkt})
                item["quotes_rate_limited"] = get_counter_labelled("quotes_rate_limited", {"market": mkt})
                # Include per-market relayer event counters when verbose JSON is requested
                item["relayer_rate_limited_events"] = get_counter_labelled("relayer_rate_limited_events", {"market": mkt})
                item["relayer_timeouts_events"] = get_counter_labelled("relayer_timeouts_events", {"market": mkt})
                item["relayer_builder_errors"] = get_counter_labelled("relayer_builder_errors", {"market": mkt})
            items.append(item)
        out = _json.dumps(items)
        print(out)
        return out
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
            rbe = get_counter_labelled("relayer_builder_errors", {"market": mkt})
            eret = get_counter_labelled("engine_retries", {"market": mkt})
            dplaced = get_counter_labelled("dutch_orders_placed", {"market": mkt})
            drh = get_counter_labelled("dutch_rulehash_changed", {"market": mkt})
            ems = get_counter_labelled("engine_execute_plan_ms_sum", {"market": mkt})
            ec = get_counter_labelled("engine_execute_plan_count", {"market": mkt})
            avg_ms = (ems / ec) if ec else 0
            ack_sum = get_counter_labelled("engine_ack_ms_sum", {"market": mkt})
            ack_cnt = get_counter_labelled("engine_ack_count", {"market": mkt})
            ack_avg = (ack_sum / ack_cnt) if ack_cnt else 0
            # global relayer limits/timeouts are process-wide; include as context
            from polybot.observability.metrics import get_counter
            rl = get_counter("relayer_rate_limited_total")
            to = get_counter("relayer_timeouts_total")
            total_resyncs = gap + csum + firstd
            resync_ratio = (total_resyncs / max(1, applied)) if applied else 0
            lines.append(f"  quotes: placed={qp} canceled={qc} skipped={qs} skipped_same={qss} rate_limited={qrl} cancel_rate_limited={qcrl}")
            lines.append(f"  orders: placed={op} filled={of} exec_avg_ms={avg_ms:.1f} exec_count={ec} retries={eret} ack_avg_ms={ack_avg:.1f}")
            rrl = get_counter_labelled("relayer_rate_limited_events", {"market": mkt})
            rto = get_counter_labelled("relayer_timeouts_events", {"market": mkt})
            lines.append(f"  relayer: acks_accepted={rak_ok} acks_rejected={rak_rej} rate_limited_total={rl} timeouts_total={to} per_market_rl={rrl} per_market_to={rto} builder_errors={rbe}")
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
        place_errs = get_counter_labelled("relayer_place_errors", {"market": mkt})
        builder_errs = get_counter_labelled("relayer_builder_errors", {"market": mkt})
        stats.append((mkt, resync_ratio, cancel_rl, rejects, place_errs, builder_errs))
    # Sort: resync ratio desc, then rejects desc, then place_errs desc, then builder errors desc, then cancel rate-limit desc
    stats.sort(key=lambda x: (-x[1], -x[3], -x[4], -x[5], -x[2], x[0]))
    top = stats[: max(1, limit)]
    # Global counters for relayer limits/timeouts
    from polybot.observability.metrics import get_counter
    rl = get_counter("relayer_rate_limited_total")
    to = get_counter("relayer_timeouts_total")
    lines = ["market_id resync_ratio rejects place_errors builder_errors cancel_rate_limited rate_limited_total timeouts_total"]
    for mkt, ratio, crl, rej, perr, berr in top:
        lines.append(f"{mkt} {ratio:.3f} {rej} {perr} {berr} {crl} {rl} {to}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_status_summary(db_url: str = ":memory:", as_json: bool = False) -> str:
    """Print a concise per-market summary using DB status and in-process metrics.

    Columns: market_id resync_ratio rejects place_errors runtime_avg_ms
    """
    con = connect_sqlite(db_url)
    rows = con.execute("SELECT market_id FROM market_status ORDER BY market_id").fetchall()
    if as_json:
        import json as _json
        items = []
        for (mkt,) in rows:
            applied = get_counter_labelled("ingestion_msg_applied", {"market": mkt})
            gap = get_counter_labelled("ingestion_resync_gap", {"market": mkt})
            csum = get_counter_labelled("ingestion_resync_checksum", {"market": mkt})
            firstd = get_counter_labelled("ingestion_resync_first_delta", {"market": mkt})
            total_resyncs = gap + csum + firstd
            resync_ratio = (total_resyncs / max(1, applied)) if applied else 0
            rejects = get_counter_labelled("relayer_acks_rejected", {"market": mkt})
            place_errs = get_counter_labelled("relayer_place_errors", {"market": mkt})
            rt_sum = get_counter_labelled("service_market_runtime_ms_sum", {"market": mkt})
            rt_cnt = get_counter_labelled("service_market_runtime_count", {"market": mkt})
            rt_avg = (rt_sum / rt_cnt) if rt_cnt else 0
            builder_errs = get_counter_labelled("relayer_builder_errors", {"market": mkt})
            items.append({
                "market_id": mkt,
                "resync_ratio": resync_ratio,
                "rejects": rejects,
                "place_errors": place_errs,
                "builder_errors": builder_errs,
                "runtime_avg_ms": rt_avg,
                "quotes_cancel_rate_limited": get_counter_labelled("quotes_cancel_rate_limited", {"market": mkt}),
                "quotes_rate_limited": get_counter_labelled("quotes_rate_limited", {"market": mkt}),
            })
        out = _json.dumps(items)
        print(out)
        return out
    lines = ["market_id resync_ratio rejects place_errors builder_errors runtime_avg_ms"]
    for (mkt,) in rows:
        applied = get_counter_labelled("ingestion_msg_applied", {"market": mkt})
        gap = get_counter_labelled("ingestion_resync_gap", {"market": mkt})
        csum = get_counter_labelled("ingestion_resync_checksum", {"market": mkt})
        firstd = get_counter_labelled("ingestion_resync_first_delta", {"market": mkt})
        total_resyncs = gap + csum + firstd
        resync_ratio = (total_resyncs / max(1, applied)) if applied else 0
        rejects = get_counter_labelled("relayer_acks_rejected", {"market": mkt})
        place_errs = get_counter_labelled("relayer_place_errors", {"market": mkt})
        builder_errs = get_counter_labelled("relayer_builder_errors", {"market": mkt})
        rt_sum = get_counter_labelled("service_market_runtime_ms_sum", {"market": mkt})
        rt_cnt = get_counter_labelled("service_market_runtime_count", {"market": mkt})
        rt_avg = (rt_sum / rt_cnt) if rt_cnt else 0
        lines.append(f"{mkt} {resync_ratio:.3f} {rejects} {place_errs} {builder_errs} {rt_avg:.1f}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_audit_tail(db_url: str = ":memory:", limit: int = 10, as_json: bool = False) -> str:
    """Print the most recent exec_audit rows in a compact form.

    Columns: ts_ms plan_id duration_ms place_ms ack_ms intents acks
    """
    con = connect_sqlite(db_url)
    try:
        rows = con.execute(
            "SELECT ts_ms, plan_id, duration_ms, place_call_ms, ack_latency_ms, request_id, intents_json, acks_json FROM exec_audit ORDER BY id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        with_rid = True
    except Exception:
        rows = con.execute(
            "SELECT ts_ms, plan_id, duration_ms, place_call_ms, ack_latency_ms, intents_json, acks_json FROM exec_audit ORDER BY id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        with_rid = False
    if as_json:
        items = []
        for row in rows:
            if with_rid:
                ts, pid, dur, plc, ack, rid, intents_json, acks_json = row
            else:
                ts, pid, dur, plc, ack, intents_json, acks_json = row
                rid = ""
            try:
                intents = len(_json.loads(intents_json or "[]"))
            except Exception:
                intents = 0
            try:
                acks = len(_json.loads(acks_json or "[]"))
            except Exception:
                acks = 0
            items.append({
                "ts_ms": ts,
                "plan_id": pid,
                "duration_ms": dur,
                "place_ms": plc,
                "ack_ms": ack,
                "request_id": rid,
                "intents": intents,
                "acks": acks,
            })
        out = _json.dumps(items)
        print(out)
        return out
    lines = ["ts_ms plan_id duration_ms place_ms ack_ms request_id intents acks"]
    for row in rows:
        if with_rid:
            ts, pid, dur, plc, ack, rid, intents_json, acks_json = row
        else:
            ts, pid, dur, plc, ack, intents_json, acks_json = row
            rid = ""
        try:
            intents = len(_json.loads(intents_json or "[]"))
        except Exception:
            intents = 0
        try:
            acks = len(_json.loads(acks_json or "[]"))
        except Exception:
            acks = 0
        lines.append(f"{ts} {pid or ''} {dur or 0} {plc or 0} {ack or 0} {rid or ''} {intents} {acks}")
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


def cmd_health(db_url: str = ":memory:", staleness_threshold_ms: int = 30000, as_json: bool = False) -> str:
    # Ensure schema exists for health checks
    con = init_db(db_url)
    issues = check_staleness(con, staleness_threshold_ms)
    if as_json:
        import json as _json
        out = _json.dumps({"ok": not bool(issues), "issues": issues})
        print(out)
        return out
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


def cmd_metrics_reset() -> str:
    metrics_reset_fn()
    msg = "OK: metrics reset"
    print(msg)
    return msg


def cmd_metrics_json() -> str:
    """Return in-process metrics counters as JSON."""
    from polybot.observability.metrics import list_counters, list_counters_labelled

    data = {
        "counters": {name: val for name, val in list_counters()},
        "labelled": [
            {"name": name, "labels": {k: v for k, v in labels}, "value": val}
            for (name, labels, val) in list_counters_labelled()
        ],
    }
    text = _json.dumps(data)
    print(text)
    return text


def cmd_config_dump(config_path: str) -> str:
    """Load a service TOML and print normalized JSON (with secrets redacted)."""
    from polybot.service.config import load_service_config
    try:
        cfg = load_service_config(config_path)
    except Exception as e:  # noqa: BLE001
        out = f"INVALID: failed to parse config: {e}"
        print(out)
        return out
    data = {
        "db_url": cfg.db_url,
        "relayer": {
            "type": cfg.relayer_type,
            "base_url": cfg.relayer_base_url,
            "dry_run": cfg.relayer_dry_run,
            "chain_id": cfg.relayer_chain_id,
            "timeout_s": cfg.relayer_timeout_s,
            "private_key": "***redacted***" if cfg.relayer_private_key else "",
        },
        "service": {
            "engine_max_retries": cfg.engine_max_retries,
            "engine_retry_sleep_ms": cfg.engine_retry_sleep_ms,
            "relayer_max_retries": cfg.relayer_max_retries,
            "relayer_retry_sleep_ms": cfg.relayer_retry_sleep_ms,
        },
        "markets": [
            {
                "market_id": m.market_id,
                "outcome_yes_id": m.outcome_yes_id,
                "ws_url": m.ws_url,
                "subscribe": m.subscribe,
                "max_messages": m.max_messages or 0,
            }
            for m in cfg.markets
        ],
    }
    text = _json.dumps(data)
    print(text)
    return text


def cmd_orders_tail(db_url: str = ":memory:", limit: int = 5, as_json: bool = False) -> str:
    con = connect_sqlite(db_url)
    rows = con.execute(
        "SELECT order_id, market_id, outcome_id, side, price, size, tif, status, created_ts_ms FROM orders ORDER BY created_ts_ms DESC, order_id DESC LIMIT ?",
        (max(1, int(limit)),),
    ).fetchall()
    if as_json:
        out = _json.dumps([
            {
                "order_id": r[0],
                "market_id": r[1],
                "outcome_id": r[2],
                "side": r[3],
                "price": r[4],
                "size": r[5],
                "tif": r[6],
                "status": r[7],
                "created_ts_ms": r[8],
            }
            for r in rows
        ])
        print(out)
        return out
    lines = ["order_id market_id outcome_id side price size tif status created_ts_ms"]
    for r in rows:
        lines.append(f"{r[0]} {r[1]} {r[2]} {r[3]} {r[4]} {r[5]} {r[6]} {r[7]} {r[8]}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_orders_cancel_client_oids(
    client_oids: str,
    db_url: str = ":memory:",
    relayer_type: str = "fake",
    base_url: str = "https://clob.polymarket.com",
    private_key: str = "",
    chain_id: int = 137,
    timeout_s: float = 10.0,
) -> str:
    """Cancel client orders by client_oid via engine+relayer and update DB statuses.

    For safety, defaults to a FakeRelayer unless explicitly set. On real relayer, ensure
    private_key is configured via secrets overlay or argument.
    """
    con = init_db(db_url)
    # Build relayer
    if relayer_type.lower() == "real":
        builder_kwargs = _builder_kwargs_from_env()
        rel = build_relayer(
            "real",
            base_url=base_url,
            private_key=private_key,
            dry_run=False,
            chain_id=chain_id,
            timeout_s=timeout_s,
            **builder_kwargs,
        )
    else:
        rel = FakeRelayer(fill_ratio=0.0)
    eng = ExecutionEngine(rel, audit_db=con)
    oids = [x.strip() for x in client_oids.split(",") if x.strip()]
    eng.cancel_client_orders(oids)
    out = f"canceled={len(oids)}"
    print(out)
    return out


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


def cmd_preflight(config_path: str, as_json: bool = False) -> str:
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
    builder_kwargs: Dict[str, str] = {}
    if cfg.relayer_type.lower() == "real":
        from polybot.adapters.polymarket.crypto import is_valid_private_key

        if not cfg.relayer_private_key or not is_valid_private_key(cfg.relayer_private_key):
            issues.append("relayer.private_key is invalid (expect 0x-prefixed 32-byte hex)")
        if int(cfg.relayer_chain_id) <= 0:
            issues.append("relayer.chain_id must be > 0")
        builder_kwargs = _collect_builder_kwargs(cfg)
        ready, reason = _ensure_builder_ready(cfg, builder_kwargs)
        if not ready and reason:
            issues.append(reason)
    # Markets
    if not cfg.markets:
        issues.append("no markets configured")

    if issues:
        if as_json:
            import json as _json
            out = _json.dumps({"ok": False, "issues": issues})
            print(out)
            return out
        header = "INVALID: preflight checks failed"
        lines = [header] + [f" - {i}" for i in issues]
        out = "\n".join(lines)
        print(out)
        return out
    if as_json:
        import json as _json
        out = _json.dumps({"ok": True})
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


def cmd_smoke_live(config_path: str, market_id: str, outcome_id: str, side: str, price: float, size: float, base_url: str, private_key: str, chain_id: Optional[int] = None, timeout_s: Optional[float] = None, as_json: bool = False) -> str:
    pre = cmd_preflight(config_path)
    if not pre.startswith("OK:"):
        return pre
    cfg = load_service_config(config_path)
    final_base_url = base_url or cfg.relayer_base_url
    final_private_key = private_key or cfg.relayer_private_key
    final_chain_id = chain_id if chain_id is not None else cfg.relayer_chain_id
    final_timeout_s = timeout_s if timeout_s is not None else cfg.relayer_timeout_s
    builder_summary = None
    allowances_summary = None
    builder_kwargs: Dict[str, str] = {}
    if cfg.relayer_type.lower() == "real":
        ok, details, error, builder_kwargs = _builder_health_status(cfg)
        if not ok:
            msg = f"builder health failed: {error}"
            print(msg)
            return msg
        builder_summary = details or {}
        allow_err, allow_data = _collect_allowances_for_smoke(final_base_url, final_private_key, final_chain_id, final_timeout_s, builder_kwargs, outcome_id)
        if allow_err:
            allowances_summary = {"error": allow_err}
        else:
            allowances_summary = allow_data
    res = cmd_relayer_dry_run(market_id, outcome_id, side, price, size, base_url=final_base_url, private_key=final_private_key, db_url=":memory:", chain_id=final_chain_id, timeout_s=final_timeout_s)
    from polybot.observability.metrics import get_counter

    rl = get_counter("relayer_rate_limited_total")
    to = get_counter("relayer_timeouts_total")
    be = get_counter("relayer_builder_errors_total")
    if as_json:
        import json as _json

        body = {
            "preflight": pre,
            "builder": builder_summary,
            "allowances": allowances_summary,
            "result": res,
            "rate_limited_total": rl,
            "timeouts_total": to,
            "builder_errors_total": be,
        }
        out = _json.dumps(body)
        print(out)
        return out
    lines = [pre]
    if builder_summary:
        lines.append(f"builder: {_safe_json_dump(builder_summary)}")
    if allowances_summary:
        lines.append(f"allowances: {_safe_json_dump(allowances_summary)}")
    lines.append(res)
    lines.append(f"metrics: rate_limited={rl} timeouts={to} builder_errors={be}")
    out = "\n".join(lines)
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


async def cmd_run_service_from_config_async(config_path: str, summary_json_output: str | None = None) -> None:
    cfg = load_service_config(config_path)
    rel_kwargs = {
        "base_url": cfg.relayer_base_url,
        "dry_run": cfg.relayer_dry_run,
        "private_key": cfg.relayer_private_key,
        "chain_id": cfg.relayer_chain_id,
        "timeout_s": cfg.relayer_timeout_s,
        "max_retries": cfg.relayer_max_retries,
        "retry_sleep_ms": cfg.relayer_retry_sleep_ms,
    }
    builder_kwargs = _builder_kwargs_from_cfg(cfg)
    env_builder = _builder_kwargs_from_env()
    builder_kwargs.update(env_builder)
    rel_kwargs.update(builder_kwargs)
    sr = ServiceRunner(
        db_url=cfg.db_url,
        params=cfg.default_spread,
        relayer_type=cfg.relayer_type,
        relayer_kwargs=rel_kwargs,
        engine_max_retries=cfg.engine_max_retries,
        engine_retry_sleep_ms=cfg.engine_retry_sleep_ms,
    )
    await sr.run_markets(cfg.markets)
    # After completion, print a concise per-market summary for operator visibility
    try:
        cmd_status_summary(db_url=cfg.db_url)
        if summary_json_output:
            text = cmd_status_summary(db_url=cfg.db_url, as_json=True)
            try:
                p = Path(summary_json_output)
                p.write_text(text, encoding="utf-8")
                print(f"wrote summary JSON to {p}")
            except Exception as e:  # noqa: BLE001
                print(f"WARN: failed to write summary JSON: {e}")
    except Exception:
        pass


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
    builder_kwargs = _builder_kwargs_from_env()
    try:
        rel = build_relayer("real", base_url=base_url, private_key=private_key, dry_run=True, chain_id=chain_id, timeout_s=timeout_s, **builder_kwargs)
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


def _try_build_real_relayer(base_url: str, private_key: str, chain_id: int = 137, timeout_s: float = 10.0, builder_kwargs: Optional[Dict[str, str]] = None):
    kwargs = builder_kwargs or _builder_kwargs_from_env()
    try:
        return build_relayer("real", base_url=base_url, private_key=private_key, dry_run=False, chain_id=chain_id, timeout_s=timeout_s, **kwargs)
    except Exception as e:  # noqa: BLE001
        return f"relayer unavailable: {e}"


def cmd_relayer_approve_usdc(
    base_url: str,
    private_key: str,
    amount: float,  # retained for backwards compatibility; not used
    retries: int = 2,
    backoff_ms: int = 100,
    chain_id: Optional[int] = None,
    timeout_s: Optional[float] = None,
    config_path: Optional[str] = None,
    get_only: bool = False,
) -> str:
    """Refresh builder-side USDC allowance via py-clob-client balance endpoints."""
    cfg, base_url, private_key, chain_id, timeout_s, builder_kwargs = _resolve_relayer_inputs(config_path, base_url, private_key, chain_id, timeout_s)
    if not private_key:
        msg = "relayer.private_key is required for allowance operations"
        print(msg)
        return msg
    try:
        from polybot.adapters.polymarket.crypto import is_valid_private_key

        if not is_valid_private_key(private_key):
            msg = "invalid private_key: expecting 0x-prefixed 32-byte hex"
            print(msg)
            return msg
    except Exception:
        pass
    cfg_stub = cfg or SimpleNamespace(relayer_type="real")
    ready, reason = _ensure_builder_ready(cfg_stub, builder_kwargs)
    if not ready:
        msg = reason or "builder credentials missing"
        print(msg)
        return msg
    rel = _build_real_relayer_cli(base_url, private_key, chain_id, timeout_s, builder_kwargs, dry_run=False)
    if isinstance(rel, str):
        print(rel)
        return rel
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    except Exception as exc:  # noqa: BLE001
        msg = f"allowance unavailable: {exc}"
        print(msg)
        return msg
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
    try:
        before, after, update_resp = _run_allowance_flow(rel, params, "usdc", retries, backoff_ms, get_only)
    except NotImplementedError as exc:
        msg = str(exc)
        print(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"relayer unavailable: {exc}"
        print(msg)
        return msg
    out = f"allowance_usdc ok before={_safe_json_dump(before)} after={_safe_json_dump(after)}"
    if update_resp is not None:
        out += f" update={_safe_json_dump(update_resp)}"
    elif get_only:
        out += " (get-only)"
    print(out)
    return out


def cmd_relayer_approve_outcome(
    base_url: str,
    private_key: str,
    token_address: str,
    amount: float,  # retained for backwards compatibility; not used
    retries: int = 2,
    backoff_ms: int = 100,
    chain_id: Optional[int] = None,
    timeout_s: Optional[float] = None,
    config_path: Optional[str] = None,
    get_only: bool = False,
) -> str:
    """Refresh outcome token allowance via py-clob-client balance endpoints."""
    if not token_address:
        msg = "token parameter is required"
        print(msg)
        return msg
    cfg, base_url, private_key, chain_id, timeout_s, builder_kwargs = _resolve_relayer_inputs(config_path, base_url, private_key, chain_id, timeout_s)
    if not private_key:
        msg = "relayer.private_key is required for allowance operations"
        print(msg)
        return msg
    try:
        from polybot.adapters.polymarket.crypto import is_valid_private_key

        if not is_valid_private_key(private_key):
            msg = "invalid private_key: expecting 0x-prefixed 32-byte hex"
            print(msg)
            return msg
    except Exception:
        pass
    cfg_stub = cfg or SimpleNamespace(relayer_type="real")
    ready, reason = _ensure_builder_ready(cfg_stub, builder_kwargs)
    if not ready:
        msg = reason or "builder credentials missing"
        print(msg)
        return msg
    rel = _build_real_relayer_cli(base_url, private_key, chain_id, timeout_s, builder_kwargs, dry_run=False)
    if isinstance(rel, str):
        print(rel)
        return rel
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    except Exception as exc:  # noqa: BLE001
        msg = f"allowance unavailable: {exc}"
        print(msg)
        return msg
    params = BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_address)
    try:
        before, after, update_resp = _run_allowance_flow(rel, params, "outcome", retries, backoff_ms, get_only)
    except NotImplementedError as exc:
        msg = str(exc)
        print(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"relayer unavailable: {exc}"
        print(msg)
        return msg
    out = f"allowance_outcome ok token={token_address} before={_safe_json_dump(before)} after={_safe_json_dump(after)}"
    if update_resp is not None:
        out += f" update={_safe_json_dump(update_resp)}"
    elif get_only:
        out += " (get-only)"
    print(out)
    return out
def cmd_relayer_live_order(
    market_id: str,
    outcome_id: str,
    side: str,
    price: float,
    size: float,
    *,
    base_url: str,
    private_key: str,
    chain_id: int = 137,
    timeout_s: float = 10.0,
    confirm_live: bool = False,
    as_json: bool = False,
    url: str | None = None,
    prefer: str | None = None,
    suppress_output: bool = False,
    **builder_kwargs,
) -> str:
    """Place a single LIVE order via real relayer.

    Safety guard: requires confirm_live=True. Uses a small, explicit call path and prints a concise summary.
    """
    setup_logging()
    if not confirm_live:
        msg = "live order blocked: add --confirm-live to proceed"
        print(msg)
        return msg
    if url:
        resolved = _resolve_market_choice(
            url=url,
            prefer=prefer,
            base_url=base_url,
            chain_id=chain_id,
            timeout_s=timeout_s,
        )
        if not resolved:
            msg = "failed to resolve market from URL; run markets-resolve --url <URL>"
            print(msg)
            return msg
        market_id = resolved.get("market_id") or market_id
        outcome_id = resolved.get("selected_outcome_id") or outcome_id
        if not market_id or not outcome_id:
            msg = "resolved URL missing market/outcome; specify IDs manually"
            print(msg)
            return msg
    env_builder = _builder_kwargs_from_env()
    builder_kwargs = {**builder_kwargs, **env_builder}
    try:
        rel = build_relayer(
            "real",
            base_url=base_url,
            private_key=private_key,
            dry_run=False,
            chain_id=chain_id,
            timeout_s=timeout_s,
            **builder_kwargs,
        )
    except Exception as e:  # noqa: BLE001
        msg = f"relayer unavailable: {e}"
        print(msg)
        return msg
    from polybot.exec.planning import ExecutionPlan, OrderIntent
    # In-memory DB for audit in this CLI path
    con = init_db(":memory:")
    from polybot.exec.engine import ExecutionEngine

    engine = ExecutionEngine(rel, audit_db=con)
    plan = ExecutionPlan(
        intents=[OrderIntent(market_id=market_id, outcome_id=outcome_id, side=side, price=price, size=size, tif="IOC")],
        expected_profit=0.0,
        rationale="live_single",
    )
    res = engine.execute_plan(plan)
    accepted = sum(1 for a in res.acks if a.accepted)
    # status breakdown
    status_counts: dict[str, int] = {}
    for a in res.acks:
        s = str(getattr(a, "status", "") or "")
        status_counts[s] = status_counts.get(s, 0) + 1
    parts = [f"live placed={len(res.acks)} accepted={accepted}"]
    # include common statuses if present
    for key in ("filled", "partial", "accepted", "rejected"):
        if status_counts.get(key):
            parts.append(f"{key}={status_counts[key]}")
    if as_json:
        import json as _json
        body = {
            "placed": len(res.acks),
            "accepted": accepted,
            "statuses": status_counts,
        }
        out = _json.dumps(body)
        if not suppress_output:
            print(out)
        return out
    else:
        out = " ".join(parts)
        if not suppress_output:
            print(out)
        return out


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


def cmd_relayer_live_order_from_config(
    config_path: str,
    market_id: str,
    outcome_id: str,
    side: str,
    price: float,
    size: float,
    *,
    confirm_live: bool = False,
    as_json: bool = False,
    url: str | None = None,
    prefer: str | None = None,
    suppress_output: bool = False,
) -> str:
    """Convenience wrapper to place a live order using credentials from service config + secrets overlay.

    Reads relayer settings from TOML (including secrets overlay), then delegates to cmd_relayer_live_order.
    """
    cfg = load_service_config(config_path)
    builder_kwargs = _collect_builder_kwargs(cfg)
    return cmd_relayer_live_order(
        market_id=market_id,
        outcome_id=outcome_id,
        side=side,
        price=price,
        size=size,
        base_url=cfg.relayer_base_url,
        private_key=cfg.relayer_private_key,
        chain_id=cfg.relayer_chain_id,
        timeout_s=cfg.relayer_timeout_s,
        confirm_live=confirm_live,
        as_json=as_json,
        url=url,
        prefer=prefer,
        suppress_output=suppress_output,
        **builder_kwargs,
    )


def _builder_health_output(ok: bool, message: str, details: dict[str, object] | None, as_json: bool) -> str:
    payload: dict[str, object] = {"ok": ok, "message": message}
    if details:
        payload.update(details)
    if as_json:
        out = _json.dumps(payload)
        print(out)
        return out
    if ok:
        summary_bits = []
        if details:
            for key in ("builder_type", "source", "address", "can_builder_auth"):
                val = details.get(key)
                if val not in (None, "", {}):
                    summary_bits.append(f"{key}={val}")
        summary = " ".join(summary_bits)
        text = f"builder ok{(': ' + summary) if summary else ''}"
        print(text)
        return text
    text = f"builder not ready: {message}"
    print(text)
    return text


def _builder_health_status(cfg) -> Tuple[bool, Optional[dict[str, object]], Optional[str], Dict[str, str]]:
    builder_kwargs = _collect_builder_kwargs(cfg)
    ready, reason = _ensure_builder_ready(cfg, builder_kwargs)
    source = _builder_source(builder_kwargs)
    if not ready:
        return False, None, reason, builder_kwargs
    if not cfg.relayer_private_key:
        return False, None, "relayer.private_key is missing", builder_kwargs
    try:
        from polybot.adapters.polymarket.crypto import is_valid_private_key

        if not is_valid_private_key(cfg.relayer_private_key):
            return False, None, "relayer.private_key is invalid", builder_kwargs
    except Exception:
        pass
    rel = _build_real_relayer_cli(
        base_url=cfg.relayer_base_url,
        private_key=cfg.relayer_private_key,
        chain_id=cfg.relayer_chain_id,
        timeout_s=cfg.relayer_timeout_s,
        builder_kwargs=builder_kwargs,
        dry_run=True,
    )
    if isinstance(rel, str):
        return False, None, rel, builder_kwargs
    client = getattr(rel, "_client", rel)
    builder_config = getattr(client, "builder_config", None)
    if builder_config is None:
        return False, None, "client missing builder_config (check credentials and py-clob-client version)", builder_kwargs
    builder_type_value = None
    try:
        btype = builder_config.get_builder_type()
        builder_type_value = getattr(btype, "value", str(btype))
    except Exception:
        builder_type_value = None
    try:
        can_auth = bool(client.can_builder_auth())
    except Exception as exc:  # noqa: BLE001
        return False, None, f"builder auth check failed: {exc}", builder_kwargs
    if not can_auth:
        return False, None, "builder configuration invalid or incomplete", builder_kwargs
    address = ""
    if hasattr(client, "get_address"):
        try:
            address = client.get_address() or ""
        except Exception:
            address = ""
    details = {
        "builder_type": builder_type_value,
        "source": source,
        "address": address,
        "can_builder_auth": can_auth,
    }
    return True, details, None, builder_kwargs


def _build_real_relayer_cli(
    base_url: str,
    private_key: str,
    chain_id: int,
    timeout_s: float,
    builder_kwargs: Dict[str, str],
    *,
    dry_run: bool,
):
    try:
        return build_relayer(
            "real",
            base_url=base_url,
            private_key=private_key,
            dry_run=dry_run,
            chain_id=chain_id,
            timeout_s=timeout_s,
            **builder_kwargs,
        )
    except Exception as exc:  # noqa: BLE001
        return f"relayer unavailable: {exc}"


def _resolve_relayer_inputs(
    config_path: Optional[str],
    base_url: Optional[str],
    private_key: Optional[str],
    chain_id: Optional[int],
    timeout_s: Optional[float],
) -> Tuple[Optional["ServiceConfig"], str, str, int, float, Dict[str, str]]:
    cfg = None
    builder_kwargs: Dict[str, str] = _builder_kwargs_from_env()
    if config_path:
        cfg = load_service_config(config_path)
        base_url = base_url or cfg.relayer_base_url
        private_key = private_key or cfg.relayer_private_key
        if chain_id is None:
            chain_id = cfg.relayer_chain_id
        if timeout_s is None:
            timeout_s = cfg.relayer_timeout_s
        builder_kwargs = _collect_builder_kwargs(cfg)
    chain_id = chain_id if chain_id is not None else 137
    timeout_s = timeout_s if timeout_s is not None else 10.0
    final_base_url = base_url or "https://clob.polymarket.com"
    final_private_key = private_key or ""
    return cfg, final_base_url, final_private_key, chain_id, timeout_s, builder_kwargs


def _build_clob_client(base_url: str, timeout_s: float) -> ClobHttpClient:
    return ClobHttpClient(base_url=base_url, timeout=timeout_s)


def _fetch_market_overview(base_url: str, market_id: str, outcome_id: str, timeout_s: float, outcome_hint: Optional[str] = None) -> Dict[str, Any]:
    client = _build_clob_client(base_url, timeout_s)
    market_payload: Dict[str, Any] = {"market_id": market_id, "outcome_id": outcome_id, "title": "", "status": "", "outcome_name": outcome_hint or ""}
    errors: Dict[str, str] = {}
    try:
        details = client.get_market(market_id) or {}
        market_payload["title"] = str(details.get("question") or details.get("title") or market_payload["title"])
        market_payload["status"] = str(details.get("status") or "")
        if not market_payload["outcome_name"]:
            tokens = details.get("tokens") or []
            if isinstance(tokens, list):
                for t in tokens:
                    if not isinstance(t, dict):
                        continue
                    tok = str(t.get("token_id") or t.get("tokenId") or t.get("id") or "")
                    if tok == outcome_id:
                        market_payload["outcome_name"] = str(t.get("name") or t.get("symbol") or t.get("displayName") or "")
                        break
    except Exception as exc:  # noqa: BLE001
        errors["market"] = str(exc)
    def _safe_call(label: str, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            errors[label] = str(exc)
            return None

    prices = {
        "buy": _safe_call("price_buy", client.get_price, outcome_id, "buy"),
        "sell": _safe_call("price_sell", client.get_price, outcome_id, "sell"),
        "midpoint": _safe_call("midpoint", client.get_midpoint, outcome_id),
        "spread": _safe_call("spread", client.get_spread, outcome_id),
    }
    payload = {"market": market_payload, "prices": prices}
    if errors:
        payload["errors"] = errors
    return payload


def _run_allowance_flow(rel, params, kind: str, retries: int, backoff_ms: int, get_only: bool):
    from polybot.observability.metrics import inc_labelled

    if not hasattr(rel, "get_balance_allowance"):
        raise NotImplementedError("get_balance_allowance not available on relayer")
    get_balance = getattr(rel, "get_balance_allowance")
    before = get_balance(params)
    if get_only:
        return before, before, None
    update_fn = getattr(rel, "update_balance_allowance", None)
    if update_fn is None:
        raise NotImplementedError("update_balance_allowance not available on relayer")
    attempt = 0
    while True:
        try:
            inc_labelled("relayer_allowance_attempts", {"kind": kind}, 1)
            update_resp = update_fn(params)
            inc_labelled("relayer_allowance_success", {"kind": kind}, 1)
            after = get_balance(params)
            return before, after, update_resp
        except Exception as exc:  # noqa: BLE001
            attempt += 1
            inc_labelled("relayer_allowance_errors", {"kind": kind}, 1)
            if attempt > retries:
                raise
            import time as _t

            _t.sleep(max(0, backoff_ms) / 1000.0)

def _collect_allowances_for_smoke(base_url: str, private_key: str, chain_id: int, timeout_s: float, builder_kwargs: Dict[str, str], outcome_id: str | None):
    rel = _build_real_relayer_cli(base_url, private_key, chain_id, timeout_s, builder_kwargs, dry_run=False)
    if isinstance(rel, str):
        return rel, None
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    except Exception as exc:  # noqa: BLE001
        return f"allowances unavailable: {exc}", None
    summary: Dict[str, object] = {}
    try:
        usdc = getattr(rel, "get_balance_allowance")(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
        summary["usdc"] = usdc
    except Exception as exc:  # noqa: BLE001
        summary["usdc_error"] = str(exc)
    if outcome_id:
        try:
            outcome = getattr(rel, "get_balance_allowance")(BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=outcome_id))
            summary["outcome"] = outcome
        except Exception as exc:  # noqa: BLE001
            summary["outcome_error"] = str(exc)
    return None, summary


def cmd_builder_health(config_path: str, as_json: bool = False) -> str:
    """Check builder credentials and instantiation for a config."""
    cfg = load_service_config(config_path)
    ok, details, error, builder_kwargs = _builder_health_status(cfg)
    if not ok:
        return _builder_health_output(False, error or "builder not ready", {"source": _builder_source(builder_kwargs)}, as_json)
    return _builder_health_output(True, "builder credentials valid", details or {}, as_json)


def _format_price_value(value: Any) -> str:
    if isinstance(value, dict):
        if "price" in value:
            return str(value.get("price"))
        if "midpoint" in value:
            return str(value.get("midpoint"))
        if "spread" in value:
            return str(value.get("spread"))
    if value is None:
        return "n/a"
    return str(value)


def _emit_market_trade_output(payload: Dict[str, Any], as_json: bool) -> str:
    if as_json:
        out = _json.dumps(payload)
        print(out)
        return out
    lines = []
    market = payload.get("market") or {}
    outcome_line = market.get("outcome_name") or market.get("outcome_id") or ""
    lines.append(f"market: {market.get('title') or ''} ({market.get('market_id')}) outcome={outcome_line}")
    prices = payload.get("prices") or {}
    lines.append(
        "prices: buy={buy} sell={sell} midpoint={mid} spread={spread}".format(
            buy=_format_price_value(prices.get("buy")),
            sell=_format_price_value(prices.get("sell")),
            mid=_format_price_value(prices.get("midpoint")),
            spread=_format_price_value(prices.get("spread")),
        )
    )
    if payload.get("errors"):
        lines.append(f"errors: {_safe_json_dump(payload['errors'])}")
    if payload.get("note"):
        lines.append(payload["note"])
    if payload.get("entry"):
        entry = payload["entry"]
        lines.append(f"entry: {entry if isinstance(entry, str) else _safe_json_dump(entry)}")
    if payload.get("close"):
        close = payload["close"]
        lines.append(f"close: {close if isinstance(close, str) else _safe_json_dump(close)}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_market_trade(
    config_path: str,
    *,
    url: Optional[str] = None,
    query: Optional[str] = None,
    market_id: Optional[str] = None,
    outcome_id: Optional[str] = None,
    prefer: Optional[str] = None,
    side: str = "buy",
    price: float,
    size: float,
    close: bool = False,
    close_price: Optional[float] = None,
    close_size: Optional[float] = None,
    confirm_live: bool = False,
    as_json: bool = False,
    base_url: Optional[str] = None,
    chain_id: Optional[int] = None,
    timeout_s: Optional[float] = None,
) -> str:
    cfg = load_service_config(config_path)
    trade_side = (side or "buy").strip().lower()
    if trade_side not in ("buy", "sell"):
        msg = "side must be 'buy' or 'sell'"
        print(msg)
        return msg
    resolved: Dict[str, Any]
    if market_id and outcome_id:
        resolved = {
            "market_id": market_id,
            "selected_outcome_id": outcome_id,
            "selected_outcome_name": "",
            "title": "",
        }
    else:
        if not url and not query:
            msg = "provide --url/--query or --market-id/--outcome-id"
            print(msg)
            return msg
        resolved = _resolve_market_choice(
            url=url,
            query=query,
            prefer=prefer,
            base_url=base_url or cfg.relayer_base_url,
            chain_id=chain_id or cfg.relayer_chain_id,
            timeout_s=timeout_s or cfg.relayer_timeout_s,
        ) or {}
        if not resolved:
            msg = "failed to resolve market from input"
            print(msg)
            return msg
    market_id = str(resolved.get("market_id") or market_id or "")
    outcome_id = str(resolved.get("selected_outcome_id") or outcome_id or "")
    if not market_id or not outcome_id:
        msg = "missing market_id/outcome_id after resolution"
        print(msg)
        return msg
    base_url_final = base_url or cfg.relayer_base_url
    chain_id_final = chain_id or cfg.relayer_chain_id
    timeout_final = timeout_s or cfg.relayer_timeout_s
    overview = _fetch_market_overview(base_url_final, market_id, outcome_id, timeout_final, resolved.get("selected_outcome_name"))
    payload: Dict[str, Any] = {
        "market": overview.get("market"),
        "prices": overview.get("prices"),
    }
    if overview.get("errors"):
        payload["errors"] = overview["errors"]
    if not confirm_live:
        payload["note"] = "Add --confirm-live to place entry/exit orders; displaying market snapshot only."
        return _emit_market_trade_output(payload, as_json)
    entry_resp = cmd_relayer_live_order_from_config(
        config_path,
        market_id,
        outcome_id,
        trade_side,
        price,
        size,
        confirm_live=True,
        as_json=as_json,
        suppress_output=True,
    )
    if as_json:
        try:
            payload["entry"] = _json.loads(entry_resp)
        except Exception:
            payload["entry"] = {"raw": entry_resp}
    else:
        payload["entry"] = entry_resp
    if close and confirm_live:
        exit_side = "sell" if trade_side == "buy" else "buy"
        exit_price = close_price if close_price is not None else price
        exit_size = close_size if close_size is not None else size
        close_resp = cmd_relayer_live_order_from_config(
            config_path,
            market_id,
            outcome_id,
            exit_side,
            exit_price,
            exit_size,
            confirm_live=True,
            as_json=as_json,
            suppress_output=True,
        )
        if as_json:
            try:
                payload["close"] = _json.loads(close_resp)
            except Exception:
                payload["close"] = {"raw": close_resp}
        else:
            payload["close"] = close_resp
    return _emit_market_trade_output(payload, as_json)


def cmd_markets_search(db_url: str, query: str, limit: int = 10, as_json: bool = False) -> str:
    """Search markets by title substring (case-insensitive) from DB.

    Returns market_id, title, status, and outcomes summary for quick targeting.
    """
    con = connect_sqlite(db_url)
    q = f"%{query.lower()}%"
    rows = con.execute(
        "SELECT m.market_id, m.title, m.status, COALESCE(s.last_update_ts_ms, 0) as updated "
        "FROM markets m LEFT JOIN market_status s ON m.market_id = s.market_id "
        "WHERE lower(m.title) LIKE ? ORDER BY updated DESC, m.market_id LIMIT ?",
        (q, max(1, int(limit))),
    ).fetchall()
    items = []
    for mid, title, status, updated in rows:
        oc = con.execute("SELECT COUNT(1) FROM outcomes WHERE market_id = ?", (mid,)).fetchone()[0]
        items.append({
            "market_id": mid,
            "title": title,
            "status": status,
            "last_update_ts_ms": int(updated or 0),
            "outcomes_count": int(oc or 0),
        })
    if as_json:
        out = _json.dumps(items)
        print(out)
        return out
    lines = ["market_id title status last_update_ms outcomes_count"]
    for it in items:
        lines.append(f"{it['market_id']} {it['title']} {it['status']} {it['last_update_ts_ms']} {it['outcomes_count']}")
    out = "\n".join(lines)
    print(out)
    return out


def cmd_markets_show(db_url: str, market_id: str, as_json: bool = False) -> str:
    """Show a single market with all outcomes from DB."""
    con = connect_sqlite(db_url)
    row = con.execute(
        "SELECT market_id, title, status FROM markets WHERE market_id = ?",
        (market_id,),
    ).fetchone()
    if not row:
        out = f"market not found: {market_id}"
        print(out)
        return out
    outs = con.execute(
        "SELECT outcome_id, name, tick_size, min_size FROM outcomes WHERE market_id = ? ORDER BY outcome_id",
        (market_id,),
    ).fetchall()
    item = {
        "market_id": row[0],
        "title": row[1],
        "status": row[2],
        "outcomes": [
            {
                "outcome_id": o[0],
                "name": o[1],
                "tick_size": float(o[2] or 0.0),
                "min_size": float(o[3] or 0.0),
            }
            for o in outs
        ],
    }
    if as_json:
        out = _json.dumps(item)
        print(out)
        return out
    lines = [f"{item['market_id']} {item['title']} {item['status']}"]
    for o in item["outcomes"]:
        lines.append(f"  - {o['outcome_id']} {o['name']} tick={o['tick_size']} min={o['min_size']}")
    out = "\n".join(lines)
    print(out)
    return out


def _resolve_market_via_next_data(url: str | None, timeout_s: float) -> dict | None:
    """Use the Polymarket web app's Next.js payload to resolve a market + outcomes."""
    if not url:
        return None
    try:
        import httpx
        import json as _local_json
    except Exception:  # pragma: no cover - dependency missing
        return None
    try:
        resp = httpx.get(url, timeout=timeout_s)
        resp.raise_for_status()
    except Exception:
        return None
    text = resp.text
    marker = "__NEXT_DATA__"
    idx = text.find(marker)
    if idx == -1:
        return None
    start = text.find("{", idx)
    end = text.find("</script>", start)
    if start == -1 or end == -1:
        return None
    try:
        payload = _local_json.loads(text[start:end])
    except Exception:
        return None
    queries = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    for query in queries:
        key = query.get("queryKey")
        if not (isinstance(key, list) and key and key[0] == "/api/event/slug"):
            continue
        event = query.get("state", {}).get("data") or {}
        markets = event.get("markets") or []
        if not markets:
            continue
        market = markets[0]
        outcomes = list(market.get("outcomes") or [])
        tokens = market.get("clobTokenIds") or market.get("clob_token_ids") or []
        if isinstance(tokens, str):
            tokens = [tok.strip().strip('"') for tok in tokens.strip("[]").split(",") if tok.strip()]
        resolved: list[dict[str, str]] = []
        for idx_out, name in enumerate(outcomes):
            tok = ""
            if isinstance(tokens, list) and idx_out < len(tokens):
                tok = str(tokens[idx_out])
            resolved.append({"outcome_id": tok, "name": str(name)})
        market_id = str(market.get("conditionId") or market.get("condition_id") or "")
        title = str(market.get("question") or market.get("title") or event.get("title") or "")
        return {
            "market_id": market_id,
            "title": title,
            "outcomes": resolved,
        }
    return None


def cmd_markets_resolve(
    *,
    url: str | None = None,
    query: str | None = None,
    prefer: str | None = None,
    use_pyclob: bool = True,
    base_url: str = "https://clob.polymarket.com",
    chain_id: int = 137,
    timeout_s: float = 10.0,
    as_json: bool = False,
    debug: bool = False,
    http_timeout_s: float | None = None,
    http_page_scans: int = 2,
) -> str:
    """Resolve market_id and outcome_id from a Polymarket URL or title query.

    Prefers py-clob-client if available (read-only calls), else returns basic signals for fallback to DB search.
    """
    setup_logging()
    results: list[dict] = []
    dbg: dict[str, object] = {}
    # Try to dynamically import py-clob client if not already available (helps after fresh install)
    if use_pyclob and _make_pyclob_client is None:
        try:
            from polybot.adapters.polymarket.real_client import make_pyclob_client as _reimp  # type: ignore

            globals()["_make_pyclob_client"] = _reimp
            if debug:
                dbg["pyclob_import"] = "ok"
        except Exception:
            if debug:
                dbg["pyclob_import"] = "import_failed"
            pass
    if use_pyclob and _make_pyclob_client is not None:
        try:
            client = _make_pyclob_client(base_url=base_url, private_key="", dry_run=True, chain_id=chain_id, timeout_s=timeout_s)
            searcher = PyClobMarketSearcher(client)
            if url:
                infos = searcher.search_by_url(url, limit=5)
                used_fallback = False
                if not infos:
                    # fallback: use the last slug segment only
                    from polybot.adapters.polymarket.market_resolver import parse_polymarket_url as _pmparse

                    meta = _pmparse(url)
                    slug = (meta.get("slug") or "")
                    if slug:
                        short = slug.split("/")[-1].replace("-", " ")
                        infos = searcher.search_by_query(short, limit=5)
                        used_fallback = True
            elif query:
                infos = searcher.search_by_query(query, limit=5)
            else:
                infos = []
            attempted_ids: list[str] = []
            if debug:
                dbg["search"] = {
                    "mode": "url" if url else ("query" if query else "none"),
                    "used_fallback_on_slug": bool(url and used_fallback if 'used_fallback' in locals() else False),
                    "results_count": len(infos),
                }
            for mi in infos:
                try:
                    sel = choose_outcome(mi.outcomes, prefer=prefer)
                    results.append(
                        {
                            "market_id": mi.market_id,
                            "title": mi.title,
                            "outcomes": [{"outcome_id": o.outcome_id, "name": o.name} for o in mi.outcomes],
                            "selected_outcome_id": sel.outcome_id if sel else None,
                            "selected_outcome_name": sel.name if sel else None,
                        }
                    )
                    attempted_ids.append(mi.market_id)
                except Exception:
                    attempted_ids.append(getattr(mi, 'market_id', ''))
                    continue
            if debug:
                dbg["attempted_ids"] = attempted_ids
        except Exception as e:
            if debug:
                dbg["client_ctor_error"] = str(e)
            pass
    slug_for_url: str | None = None
    if url:
        parsed = parse_polymarket_url(url)
        slug_for_url = (parsed.get("slug") or "").lower()
    if results and slug_for_url:
        segments = [seg.replace("-", " ").strip() for seg in slug_for_url.split("/") if seg]
        segments = [seg.lower() for seg in segments if seg]
        def _matches_slug(entry: dict) -> bool:
            title = str(entry.get("title") or "").lower()
            market_id = str(entry.get("market_id") or "").lower()
            return any(seg in title or seg in market_id for seg in segments)
        if segments and not any(_matches_slug(r) for r in results):
            results.clear()
    # HTTP fallback: try a single markets page and match by slug or query (no per-market details)
    if not results:
        try:
            http = ClobHttpClient(base_url=base_url, timeout=(http_timeout_s or timeout_s))
            payload = http.get_simplified_markets(limit=100)
            data = payload.get("data") or []
            cursor = payload.get("next_cursor")
            # Prepare needle
            needle = ""
            if url:
                meta = parse_polymarket_url(url)
                slug = (meta.get("slug") or "").split("/")[-1]
                needle = slug.replace("-", " ").lower()
            elif query:
                needle = query.lower()
            matches = []
            scans = 0
            for m in data:
                q = str(m.get("question") or m.get("title") or m.get("slug") or "").lower()
                if needle and needle in q:
                    matches.append(m)
            # If no match, scan up to 2 more pages (bounded)
            while not matches and cursor and scans < http_page_scans:
                nxt = http.get_simplified_markets(cursor=cursor, limit=100)
                data2 = nxt.get("data") or []
                for m in data2:
                    q = str(m.get("question") or m.get("title") or m.get("slug") or "").lower()
                    if needle and needle in q:
                        matches.append(m)
                cursor = nxt.get("next_cursor")
                scans += 1
            # Build minimal MarketInfo-like dicts from matches using clobTokenIds if present
            for m in matches[:5]:
                cond = str(m.get("condition_id") or m.get("id") or "").strip()
                title = str(m.get("question") or m.get("title") or "")
                outs = []
                names = m.get("outcomes") if isinstance(m.get("outcomes"), list) else []
                cti = m.get("clobTokenIds") if isinstance(m.get("clobTokenIds"), str) else ""
                tokens_list = [x.strip() for x in cti.split(",") if x.strip()] if cti else []
                if names and tokens_list and len(names) == len(tokens_list):
                    for i, name in enumerate(names):
                        outs.append({"outcome_id": tokens_list[i], "name": name})
                else:
                    for name in (names or []):
                        outs.append({"outcome_id": "", "name": name})
                sel_id = outs[0]["outcome_id"] if outs and outs[0]["outcome_id"] else None
                sel_name = outs[0]["name"] if outs else None
                results.append({
                    "market_id": cond,
                    "title": title,
                    "outcomes": outs,
                    "selected_outcome_id": sel_id,
                    "selected_outcome_name": sel_name,
                })
            if debug:
                dbg["http_fallback"] = {"matches": len(matches)}
        except Exception as e:
            if debug:
                dbg["http_fallback_error"] = str(e)
    if not results and url:
        next_payload = _resolve_market_via_next_data(url, timeout_s=http_timeout_s or timeout_s)
        if next_payload:
            outs = next_payload.get("outcomes") or []
            sel = None
            try:
                sel = choose_outcome(
                    [OutcomeInfo(outcome_id=o["outcome_id"], name=o["name"]) for o in outs],
                    prefer=prefer,
                )
            except Exception:
                sel = None
            sel_id = sel.outcome_id if sel else (outs[0]["outcome_id"] if outs else None)
            sel_name = sel.name if sel else (outs[0]["name"] if outs else None)
            results.append(
                {
                    "market_id": next_payload.get("market_id"),
                    "title": next_payload.get("title"),
                    "outcomes": outs,
                    "selected_outcome_id": sel_id,
                    "selected_outcome_name": sel_name,
                }
            )
            if debug:
                dbg["next_data"] = {"used": True}
        elif debug:
            dbg["next_data"] = {"used": False}

    if not results:
        hint = {}
        if url:
            hint = parse_polymarket_url(url)
        msg = "py-clob-client unavailable or no matches; try refresh-markets + markets-search"
        if debug:
            results.append({"hint": hint, "message": msg, "debug": dbg})
        else:
            results.append({"hint": hint, "message": msg})
    if as_json:
        out = _json.dumps(results)
        print(out)
        return out
    # Human-readable summary
    if results and "market_id" in results[0]:
        lines = ["market_id title selected_outcome"]
        for r in results:
            lines.append(f"{r['market_id']} {r['title']} {r.get('selected_outcome_id') or ''}")
        out = "\n".join(lines)
        print(out)
        return out
    out = _json.dumps(results)
    print(out)
    return out


def cmd_diag_markets(
    *,
    out_file: str,
    url: str,
    db_url: str = ":memory:",
    gamma_base_url: str = "https://gamma-api.polymarket.com",
    clob_base_url: str = "https://clob.polymarket.com",
    prefer: str = "yes",
    timeout_s: float = 8.0,
    clob_max_pages: int = 1,
    clob_details_limit: int = 3,
) -> str:
    """Run a bounded diagnostic sequence and write a detailed log.

    Steps:
      1) Gamma-only sync (no CLOB), short timeout
      2) CLOB HTTP fallback sync with tight budgets
      3) markets-resolve with --debug
    """
    import time as _t
    lines: list[str] = []
    def _stamp(msg: str) -> None:
        ts = _t.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"[{ts}] {msg}")

    _stamp("diag start")
    try:
        _stamp("gamma-only sync")
        cmd_markets_sync(
            db_url=db_url,
            gamma_base_url=gamma_base_url,
            use_pyclob=False,
            use_clob_http=False,
            clob_base_url=clob_base_url,
            timeout_s=timeout_s,
            once=True,
            clob_max_pages=0,
        )
    except Exception as e:  # noqa: BLE001
        _stamp(f"gamma-only error: {e}")
    try:
        _stamp("clob-http sync (bounded)")
        cmd_markets_sync(
            db_url=db_url,
            gamma_base_url=gamma_base_url,
            use_pyclob=False,
            use_clob_http=True,
            clob_base_url=clob_base_url,
            timeout_s=timeout_s,
            once=True,
            clob_max_pages=max(0, int(clob_max_pages)),
            clob_details_limit=max(0, int(clob_details_limit)),
        )
    except Exception as e:  # noqa: BLE001
        _stamp(f"clob-http error: {e}")
    try:
        _stamp("resolve --debug")
        out = cmd_markets_resolve(url=url, prefer=prefer, as_json=True, debug=True, http_timeout_s=timeout_s)
        lines.append(out)
    except Exception as e:  # noqa: BLE001
        _stamp(f"resolve error: {e}")
    _stamp("diag end")
    try:
        p = Path(out_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass
    text = "\n".join(lines)
    print(text)
    return text


def cmd_markets_sync(
    *,
    db_url: str,
    gamma_base_url: str = "https://gamma-api.polymarket.com",
    use_pyclob: bool = True,
    use_clob_http: bool = True,
    clob_base_url: str = "https://clob.polymarket.com",
    chain_id: int = 137,
    timeout_s: float = 10.0,
    once: bool = True,
    interval_ms: int = 30000,
    clob_max_pages: int = 2,
    clob_page_limit: int = 50,
    clob_details_limit: int = 10,
) -> str:
    """Synchronize markets from Gamma and enrich outcomes with token IDs via CLOB.

    - when once=True: run single sync and exit
    - when once=False: loop with interval_ms between iterations
    """
    setup_logging()
    import httpx

    con = init_db(db_url)
    ghc = GammaHttpClient(base_url=gamma_base_url, client=httpx.Client(base_url=gamma_base_url, timeout=timeout_s))
    # Build optional CLOB client for enrichment
    clob = None
    if use_pyclob:
        try:
            from polybot.adapters.polymarket.real_client import make_pyclob_client as _reimp  # type: ignore

            clob = _reimp(base_url=clob_base_url, private_key="", dry_run=True, chain_id=chain_id, timeout_s=timeout_s)
        except Exception:
            clob = None
    # If pyclob not available and HTTP fallback allowed, use ClobHttpClient (implements same proto)
    if clob is None and use_clob_http:
        try:
            clob = ClobHttpClient(base_url=clob_base_url, client=httpx.Client(base_url=clob_base_url, timeout=timeout_s))
        except Exception:
            clob = None

    def _run_once() -> Dict[str, int]:
        return sync_markets(
            con,
            ghc,
            clob,
            clob_max_pages=clob_max_pages,
            clob_page_limit=clob_page_limit,
            clob_details_limit=clob_details_limit,
        )

    if once:
        stats = _run_once()
        out = f"markets_sync source={stats.get('source','gamma')} gamma={stats['gamma_count']} enriched={stats['enriched']}"
        print(out)
        return out
    else:
        while True:
            stats = _run_once()
            print(f"markets_sync source={stats.get('source','gamma')} gamma={stats['gamma_count']} enriched={stats['enriched']}")
            import time as _t

            _t.sleep(max(1000, int(interval_ms)) / 1000.0)
        # unreachable
        return ""


def cmd_tgbot_serve(
    host: str,
    port: int,
    secret: str,
    allowed: str,
    market_id: str,
    outcome_yes_id: str,
) -> int:
    """Serve a minimal Telegram-like webhook that forwards text to BotAgent.

    Safety: uses an in-process FakeRelayer engine. For real trading, wire the
    service config and engine separately and gate live actions with approvals.
    """
    setup_logging()
    con = init_db(":memory:")
    engine = ExecutionEngine(FakeRelayer(fill_ratio=0.0), audit_db=con)
    agent = BotAgent(engine, BotContext(market_id=market_id, outcome_yes_id=outcome_yes_id))
    allowed_ids: list[int] = []
    if allowed.strip():
        try:
            allowed_ids = [int(x) for x in allowed.split(",") if x.strip()]
        except Exception:
            allowed_ids = []
    server, _ = start_tg_server(agent, host=host, port=port, secret_path=secret, allowed_ids=allowed_ids)
    actual_port = server.server_address[1]
    print(f"tgbot-serve listening on http://{host}:{actual_port}{secret} (allowed={allowed_ids or 'any'})")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_tg_server(server)
    return actual_port





