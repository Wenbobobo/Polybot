from __future__ import annotations

import argparse

from .commands import cmd_replay, cmd_ingest_ws
from .commands import cmd_status, cmd_refresh_markets, cmd_quoter_run_ws_async, cmd_health, cmd_metrics, cmd_record_ws_async, cmd_quoter_run_replay_async, cmd_mock_ws_async
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

    p_health = sub.add_parser("health", help="Health check: staleness")
    p_health.add_argument("--db-url", default=":memory:")
    p_health.add_argument("--staleness-ms", type=int, default=30000)

    sub.add_parser("metrics", help="Print in-process metrics counters")

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


if __name__ == "__main__":
    main()
