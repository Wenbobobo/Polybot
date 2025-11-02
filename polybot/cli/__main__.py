from __future__ import annotations

import argparse

from .commands import cmd_replay, cmd_ingest_ws
from .commands import (
    cmd_status,
    cmd_refresh_markets,
    cmd_quoter_run_ws_async,
    cmd_health,
    cmd_metrics,
    cmd_record_ws_async,
    cmd_quoter_run_replay_async,
    cmd_mock_ws_async,
    cmd_metrics_export,
    cmd_metrics_serve,
    cmd_migrate,
    cmd_dutch_run_replay_async,
    cmd_relayer_dry_run,
    cmd_status_top,
    cmd_tgbot_run_local,
    cmd_relayer_approve_usdc,
    cmd_relayer_approve_outcome,
    cmd_relayer_live_order,
)
from polybot.cli.commands import cmd_run_service_from_config_async


def main() -> None:
    parser = argparse.ArgumentParser(prog="polybot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_replay = sub.add_parser("replay", help="Replay JSONL orderbook events into DB")
    p_replay.add_argument("file")
    p_replay.add_argument("market_id")
    p_replay.add_argument("--db-url", default=":memory:")

    p_ws = sub.add_parser("ingest-ws", help="Ingest WebSocket stream of orderbook messages")
    p_ws.add_argument("url")
    p_ws.add_argument("market_id")
    p_ws.add_argument("--snapshot-json")
    p_ws.add_argument("--db-url", default=":memory:")
    p_ws.add_argument("--max-messages", type=int)

    p_status = sub.add_parser("status", help="Show market ingestion status")
    p_status.add_argument("--db-url", default=":memory:")
    p_status.add_argument("--verbose", action="store_true")
    p_top = sub.add_parser("status-top", help="Show top markets by resync ratio and cancel rate-limit")
    p_top.add_argument("--db-url", default=":memory:")
    p_top.add_argument("--limit", type=int, default=5)

    p_health = sub.add_parser("health", help="Health check: staleness")
    p_health.add_argument("--db-url", default=":memory:")
    p_health.add_argument("--staleness-ms", type=int, default=30000)

    sub.add_parser("metrics", help="Print in-process metrics counters")
    sub.add_parser("metrics-export", help="Print Prometheus text exposition of metrics")
    p_mserve = sub.add_parser("metrics-serve", help="Serve /metrics over HTTP (local only)")
    p_mserve.add_argument("--host", default="127.0.0.1")
    p_mserve.add_argument("--port", type=int, default=0)

    p_mts = sub.add_parser("migrate-timescale", help="Print optional Timescale migration SQL")

    p_pf = sub.add_parser("preflight", help="Validate a service config TOML before running live")
    p_pf.add_argument("--config", required=True)

    p_migrate = sub.add_parser("migrate", help="Run or print DB migrations")
    p_migrate.add_argument("--db-url", required=True)
    p_migrate.add_argument("--print-sql", action="store_true")
    p_migrate.add_argument("--apply", action="store_true")

    p_rec = sub.add_parser("record-ws", help="Record WS messages to JSONL (optionally translate Polymarket -> internal)")
    p_rec.add_argument("url")
    p_rec.add_argument("outfile")
    p_rec.add_argument("--max-messages", type=int)
    p_rec.add_argument("--subscribe", action="store_true")
    p_rec.add_argument("--no-translate", action="store_true")

    p_qrep = sub.add_parser("quoter-run-replay", help="Run spread quoter from JSONL events")
    p_qrep.add_argument("file")
    p_qrep.add_argument("market_id")
    p_qrep.add_argument("outcome_yes_id")
    p_qrep.add_argument("--db-url", default=":memory:")

    p_mws = sub.add_parser("mock-ws", help="Run a simple mock WS server emitting Polymarket-like messages")
    p_mws.add_argument("--file")
    p_mws.add_argument("--host", default="127.0.0.1")
    p_mws.add_argument("--port", type=int, default=9000)
    p_refresh = sub.add_parser("refresh-markets", help="Refresh markets catalog from Gamma")
    p_refresh.add_argument("base_url")
    p_refresh.add_argument("--db-url", default=":memory:")

    p_quoter = sub.add_parser("quoter-run-ws", help="Run spread quoter against a WS stream (Polymarket-like)")
    p_quoter.add_argument("url")
    p_quoter.add_argument("market_id")
    p_quoter.add_argument("outcome_yes_id")
    p_quoter.add_argument("--db-url", default=":memory:")
    p_quoter.add_argument("--max-messages", type=int)
    p_quoter.add_argument("--subscribe", action="store_true")

    p_service = sub.add_parser("run-service", help="Run multi-market service from TOML config")
    p_service.add_argument("--config", required=True)

    p_dutch = sub.add_parser("dutch-run-replay", help="Run dutch-book detector from multi-outcome JSONL events")
    p_dutch.add_argument("file")
    p_dutch.add_argument("market_id")
    p_dutch.add_argument("--outcomes", help="Comma-separated outcome IDs; if omitted, read from DB")
    p_dutch.add_argument("--db-url", default=":memory:")
    p_dutch.add_argument("--min-profit-usdc", type=float, default=0.02)
    p_dutch.add_argument("--default-size", type=float, default=1.0)
    p_dutch.add_argument("--safety-margin-usdc", type=float, default=0.0)
    p_dutch.add_argument("--fee-bps", type=float, default=0.0)
    p_dutch.add_argument("--slippage-ticks", type=int, default=0)
    p_dutch.add_argument("--allow-other", action="store_true")
    p_dutch.add_argument("--verbose", action="store_true")

    p_rdry = sub.add_parser("relayer-dry-run", help="Dry-run a single order via configured 'real' relayer")
    p_rdry.add_argument("market_id")
    p_rdry.add_argument("outcome_id")
    p_rdry.add_argument("side", choices=["buy", "sell"])
    p_rdry.add_argument("price", type=float)
    p_rdry.add_argument("size", type=float)
    p_rdry.add_argument("--base-url", default="https://clob.polymarket.com")
    p_rdry.add_argument("--private-key", default="")
    p_rdry.add_argument("--db-url", default=":memory:")
    p_rdry.add_argument("--chain-id", type=int, default=137)
    p_rdry.add_argument("--timeout-s", type=float, default=10.0)

    p_ausdc = sub.add_parser("relayer-approve-usdc", help="Approve USDC spend (stub if real client unavailable)")
    p_ausdc.add_argument("--base-url", default="https://clob.polymarket.com")
    p_ausdc.add_argument("--private-key", default="")
    p_ausdc.add_argument("--amount", type=float, required=True)

    p_aout = sub.add_parser("relayer-approve-outcome", help="Approve outcome token spend (stub if real client unavailable)")
    p_aout.add_argument("--base-url", default="https://clob.polymarket.com")
    p_aout.add_argument("--private-key", default="")
    p_aout.add_argument("--token", required=True)
    p_aout.add_argument("--amount", type=float, required=True)

    p_rlive = sub.add_parser("relayer-live-order", help="Place a single LIVE order (requires --confirm-live)")
    p_rlive.add_argument("market_id")
    p_rlive.add_argument("outcome_id")
    p_rlive.add_argument("side", choices=["buy", "sell"])
    p_rlive.add_argument("price", type=float)
    p_rlive.add_argument("size", type=float)
    p_rlive.add_argument("--base-url", default="https://clob.polymarket.com")
    p_rlive.add_argument("--private-key", default="")
    p_rlive.add_argument("--chain-id", type=int, default=137)
    p_rlive.add_argument("--timeout-s", type=float, default=10.0)
    p_rlive.add_argument("--confirm-live", action="store_true")

    p_merge = sub.add_parser("conversions-merge", help="Simulate CTF merge (YES/NO -> USDC) using fake or real CTF")
    p_merge.add_argument("market_id")
    p_merge.add_argument("yes_id")
    p_merge.add_argument("no_id")
    p_merge.add_argument("size", type=float)

    p_split = sub.add_parser("conversions-split", help="Simulate CTF split (USDC -> YES/NO) using fake or real CTF")
    p_split.add_argument("market_id")
    p_split.add_argument("yes_id")
    p_split.add_argument("no_id")
    p_split.add_argument("usdc_amount", type=float)

    p_smoke = sub.add_parser("smoke-live", help="Preflight + single relayer dry-run for live readiness")
    p_smoke.add_argument("--config", required=True)
    p_smoke.add_argument("market_id")
    p_smoke.add_argument("outcome_id")
    p_smoke.add_argument("side", choices=["buy", "sell"])
    p_smoke.add_argument("price", type=float)
    p_smoke.add_argument("size", type=float)
    p_smoke.add_argument("--base-url", default="https://clob.polymarket.com")
    p_smoke.add_argument("--private-key", default="")
    p_smoke.add_argument("--chain-id", type=int, default=137)
    p_smoke.add_argument("--timeout-s", type=float, default=10.0)

    p_tg = sub.add_parser("tgbot-run-local", help="Run offline Telegram-like updates from JSONL and print responses")
    p_tg.add_argument("updates_file")
    p_tg.add_argument("market_id")
    p_tg.add_argument("outcome_yes_id")
    p_tg.add_argument("--db-url", default=":memory:")

    args = parser.parse_args()
    if args.cmd == "replay":
        cmd_replay(args.file, args.market_id, db_url=args.db_url)
    elif args.cmd == "ingest-ws":
        cmd_ingest_ws(args.url, args.market_id, snapshot_json=args.snapshot_json, db_url=args.db_url, max_messages=args.max_messages)
    elif args.cmd == "status":
        cmd_status(db_url=args.db_url, verbose=args.verbose)
    elif args.cmd == "health":
        cmd_health(db_url=args.db_url, staleness_threshold_ms=args.staleness_ms)
    elif args.cmd == "metrics":
        cmd_metrics()
    elif args.cmd == "metrics-export":
        cmd_metrics_export()
    elif args.cmd == "metrics-serve":
        cmd_metrics_serve(host=args.host, port=args.port)
    elif args.cmd == "migrate-timescale":
        from .commands import cmd_migrate_timescale_print
        cmd_migrate_timescale_print()
    elif args.cmd == "preflight":
        from .commands import cmd_preflight
        cmd_preflight(args.config)
    elif args.cmd == "conversions-merge":
        from .commands import cmd_conversions_merge
        cmd_conversions_merge(args.market_id, args.yes_id, args.no_id, args.size)
    elif args.cmd == "conversions-split":
        from .commands import cmd_conversions_split
        cmd_conversions_split(args.market_id, args.yes_id, args.no_id, args.usdc_amount)
    elif args.cmd == "smoke-live":
        from .commands import cmd_smoke_live
        cmd_smoke_live(
            args.config,
            args.market_id,
            args.outcome_id,
            args.side,
            args.price,
            args.size,
            base_url=args.base_url,
            private_key=args.private_key,
            chain_id=args.chain_id,
            timeout_s=args.timeout_s,
        )
    elif args.cmd == "status-top":
        cmd_status_top(db_url=args.db_url, limit=args.limit)
    elif args.cmd == "migrate":
        cmd_migrate(db_url=args.db_url, print_sql=args.print_sql, apply=args.apply)
    elif args.cmd == "record-ws":
        import asyncio
        asyncio.run(cmd_record_ws_async(args.url, args.outfile, max_messages=args.max_messages, subscribe=args.subscribe, translate=not args.no_translate))
    elif args.cmd == "quoter-run-replay":
        import asyncio
        asyncio.run(cmd_quoter_run_replay_async(args.file, args.market_id, args.outcome_yes_id, db_url=args.db_url))
    elif args.cmd == "mock-ws":
        import asyncio
        asyncio.run(cmd_mock_ws_async(messages_file=args.file, host=args.host, port=args.port))
    elif args.cmd == "refresh-markets":
        cmd_refresh_markets(base_url=args.base_url, db_url=args.db_url)
    elif args.cmd == "quoter-run-ws":
        import asyncio
        asyncio.run(cmd_quoter_run_ws_async(args.url, args.market_id, args.outcome_yes_id, db_url=args.db_url, max_messages=args.max_messages, subscribe=args.subscribe))
    elif args.cmd == "run-service":
        import asyncio
        asyncio.run(cmd_run_service_from_config_async(args.config))
    elif args.cmd == "dutch-run-replay":
        import asyncio
        asyncio.run(
            cmd_dutch_run_replay_async(
                args.file,
                args.market_id,
                outcomes_csv=args.outcomes,
                db_url=args.db_url,
                min_profit_usdc=args.min_profit_usdc,
                default_size=args.default_size,
                safety_margin_usdc=args.safety_margin_usdc,
                fee_bps=args.fee_bps,
                slippage_ticks=args.slippage_ticks,
                allow_other=args.allow_other,
                verbose=args.verbose,
            )
        )
    elif args.cmd == "relayer-approve-usdc":
        cmd_relayer_approve_usdc(base_url=args.base_url, private_key=args.private_key, amount=args.amount)
    elif args.cmd == "relayer-approve-outcome":
        cmd_relayer_approve_outcome(base_url=args.base_url, private_key=args.private_key, token_address=args.token, amount=args.amount)
    elif args.cmd == "relayer-live-order":
        cmd_relayer_live_order(
            args.market_id,
            args.outcome_id,
            args.side,
            args.price,
            args.size,
            base_url=args.base_url,
            private_key=args.private_key,
            chain_id=args.chain_id,
            timeout_s=args.timeout_s,
            confirm_live=args.confirm_live,
        )
        )
    elif args.cmd == "relayer-dry-run":
        cmd_relayer_dry_run(
            market_id=args.market_id,
            outcome_id=args.outcome_id,
            side=args.side,
            price=args.price,
            size=args.size,
            base_url=args.base_url,
            private_key=args.private_key,
            db_url=args.db_url,
        )
    elif args.cmd == "tgbot-run-local":
        cmd_tgbot_run_local(args.updates_file, args.market_id, args.outcome_yes_id, db_url=args.db_url)


if __name__ == "__main__":
    main()
