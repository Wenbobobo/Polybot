# Command Reference

This document lists the CLI commands available for Polybot, grouped by workflow. Most users will rely on the Telegram bot and a few flows (preflight, smoke-live, run-service). Use this as a reference or for troubleshooting.

## Setup & Config
- Builder credentials
  - Local signing：在 `config/secrets.local.toml`（或环境变量）中提供 `api_key / api_secret / api_passphrase`
  - 远程 Builder：提供 `url / token`（亦可通过 `POLY_BUILDER_REMOTE_URL` 与 `POLY_BUILDER_TOKEN` 设置）
  - 环境变量示例：
    ```
    setx POLY_BUILDER_API_KEY "<key>"
    setx POLY_BUILDER_SECRET "<secret>"
    setx POLY_BUILDER_PASSPHRASE "<passphrase>"
    ```
- Preflight（验证配置）：
  - `uv run python -m polybot.cli preflight --config config/service.toml`
- Smoke（预检查 + dry-run）：
  - `uv run python -m polybot.cli smoke-live --config config/service.toml mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x... --json`
- Live order（严格遵循参数顺序：`market_id outcome_id side price size`）：
  - 直接指定：`uv run python -m polybot.cli relayer-live-order <mid> <oid> buy 0.39 5 --base-url ... --private-key ... --confirm-live --as-json`
  - 读取配置：`uv run python -m polybot.cli relayer-live-order-config --config config/service.toml <mid> <oid> buy 0.39 5 --confirm-live --json`
  - 可追加 `--url "https://polymarket.com/event/..."` 自动解析 IDs（命令中的 `<mid> <oid>` 会被覆盖）
  - 如输出 `invalid choice (choose from buy, sell)`，表示参数顺序错误，请重新输入。

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
- Refresh markets from Gamma and list:
  - `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
  - `uv run python -m polybot.cli markets-list --db-url sqlite:///./polybot.db --limit 10 --json`
  - Search by title: `uv run python -m polybot.cli markets-search --db-url sqlite:///./polybot.db --query hype --json`
  - Show one market: `uv run python -m polybot.cli markets-show <market_id> --db-url sqlite:///./polybot.db --json`
  - Sync (bounded):
    - `uv run python -m polybot.cli markets-sync --db-url sqlite:///./polybot.db --once --clob-max-pages 1 --clob-details-limit 0`
  - Diagnostics (writes a log):
    - `uv run python -m polybot.cli diag-markets --out-file recordings/diag.txt --url "https://polymarket.com/event/..." --timeout-s 8 --clob-max-pages 1 --clob-details-limit 3`
  - Resolve via CLOB (no DB needed):
    - URL: `uv run python -m polybot.cli markets-resolve --url "https://polymarket.com/event/..." --prefer yes --json`
    - Query: `uv run python -m polybot.cli markets-resolve --query "coinbase hype 2025" --prefer no --json`
  - Search by title: `uv run python -m polybot.cli markets-search --db-url sqlite:///./polybot.db --query hype --json`
  - Show one market: `uv run python -m polybot.cli markets-show <market_id> --db-url sqlite:///./polybot.db --json`

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
- Allowance refresh（builder 账户）:
  - USDC：`uv run python -m polybot.cli relayer-approve-usdc --config config/service.toml --get-only`
  - Outcome：`uv run python -m polybot.cli relayer-approve-outcome --config config/service.toml --token 0x...`
  - `--get-only` 仅查看额度，不触发 `/balance-allowance/update`；若不加则会调用官方 `update_balance_allowance` 后再读一次额度。
- One-shot trade：
  - `uv run python -m polybot.cli market-trade --config config/service.toml --url "https://polymarket.com/event/foo" --side buy --price 0.35 --size 2 --close --close-price 0.45 --confirm-live --json`
  - 自动解析市场/Outcome → 获取 `/price`/`/midpoint`/`/spread` 最新数据 → 在 `--confirm-live` 下建仓并可选 `--close` 平仓；`--json` 返回结构化结果，默认文本模式。

## Observability
- Status & Health:
  - `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db [--verbose]`
  - JSON: `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db --json [--verbose]` (verbose JSON includes relayer per-market events)
  - `uv run python -m polybot.cli status-top --db-url sqlite:///./polybot.db --limit 10`
  - `uv run python -m polybot.cli status-summary --db-url sqlite:///./polybot.db`
  - `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`
- Metrics:
  - `uv run python -m polybot.cli metrics`
  - `uv run python -m polybot.cli metrics-export`
  - `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 8000` (endpoints: `/metrics`, `/health`)
  - `uv run python -m polybot.cli metrics-reset` (clear in-process counters)
  - `uv run python -m polybot.cli metrics-json` (counters as JSON)
  - HTTP JSON: GET `/status` from metrics-serve for counters JSON
 - Exec Audit:
  - `uv run python -m polybot.cli audit-tail --db-url sqlite:///./polybot.db --limit 5`
  - Grafana: import `observability/grafana-dashboard.json`

## Config & Database
- Config dump (redacted):
  - `uv run python -m polybot.cli config-dump --config config/service.toml`
- Orders:
  - Tail: `uv run python -m polybot.cli orders-tail --db-url sqlite:///./polybot.db --limit 5 [--json]`
  - Cancel: `uv run python -m polybot.cli orders-cancel c1,c2 --db-url sqlite:///./polybot.db --relayer real --private-key 0x...`
- Migrations (Postgres):
  - Print SQL: `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --print-sql`
  - Apply (requires psycopg): `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --apply`

## Telegram (offline)
- Simulate updates:
  - `uv run python -m polybot.cli tgbot-run-local updates.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
 - Serve webhook (offline engine, whitelist by IDs):
   - `uv run python -m polybot.cli tgbot-serve --host 127.0.0.1 --port 8001 --secret /tg --allowed 123456789 --market-id mkt-1 --outcome-yes-id yes`
