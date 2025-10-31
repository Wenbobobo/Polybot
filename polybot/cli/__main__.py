from __future__ import annotations

import argparse

from .commands import cmd_replay, cmd_ingest_ws
from .commands import cmd_status


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

    args = parser.parse_args()
    if args.cmd == "replay":
        cmd_replay(args.file, args.market_id, db_url=args.db_url)
    elif args.cmd == "ingest-ws":
        cmd_ingest_ws(args.url, args.market_id, snapshot_json=args.snapshot_json, db_url=args.db_url, max_messages=args.max_messages)
    elif args.cmd == "status":
        cmd_status(db_url=args.db_url)


if __name__ == "__main__":
    main()
