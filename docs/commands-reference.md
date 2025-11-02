# Command Reference

This document lists the CLI commands available for Polybot, grouped by workflow. Most users will rely on the Telegram bot and a few flows (preflight, smoke-live, run-service). Use this as a reference or for troubleshooting.

## Setup & Config
- Preflight (validate service config):
  - `uv run python -m polybot.cli preflight --config config/service.toml`
- Smoke live (preflight + one dry-run order):
  - `uv run python -m polybot.cli smoke-live --config config/service.toml mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x...`
- Live order (requires `--confirm-live`):
  - `uv run python -m polybot.cli relayer-live-order mkt-1 yes buy 0.01 0.01 --base-url https://clob.polymarket.com --private-key 0x... --confirm-live`

## Service
- Run service from config:
  - `uv run python -m polybot.cli run-service --config config/service.toml`

## Ingestion & Tools
- Start mock WS:
  - `uv run python -m polybot.cli mock-ws --port 9000`
- Ingest WS:
  - `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
- Record WS:
  - `uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 out.jsonl --max-messages 3 --subscribe`
- Replay JSONL:
  - `uv run python -m polybot.cli replay recordings/sample.jsonl mkt-1 --db-url sqlite:///./polybot.db`

## Strategies
- Spread quoter (WS simulate):
  - `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9000 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- Spread quoter (replay):
  - `uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
- Dutch Book (replay):
  - `uv run python -m polybot.cli dutch-run-replay recordings/multi.jsonl mkt-1 --db-url sqlite:///./polybot.db --safety-margin-usdc 0.01 --fee-bps 20 --slippage-ticks 1`

## Relayer (real client)
- Dry-run order:
  - `uv run python -m polybot.cli relayer-dry-run mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x... --db-url sqlite:///./polybot.db`
- Approvals:
  - USDC: `uv run python -m polybot.cli relayer-approve-usdc --base-url https://clob.polymarket.com --private-key 0x... --amount 100`
  - Outcome: `uv run python -m polybot.cli relayer-approve-outcome --base-url https://clob.polymarket.com --private-key 0x... --token 0x... --amount 10`

## Observability
- Status & Health:
  - `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db [--verbose]`
  - `uv run python -m polybot.cli status-top --db-url sqlite:///./polybot.db --limit 10`
  - `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`
- Metrics:
  - `uv run python -m polybot.cli metrics`
  - `uv run python -m polybot.cli metrics-export`
  - `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 8000` (endpoints: `/metrics`, `/health`)
  - Grafana: import `observability/grafana-dashboard.json`

## Database
- Migrations (Postgres):
  - Print SQL: `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --print-sql`
  - Apply (requires psycopg): `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --apply`

## Telegram (offline)
- Simulate updates:
  - `uv run python -m polybot.cli tgbot-run-local updates.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
