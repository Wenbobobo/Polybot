Polybot (Phase 1 MVP)
=====================

Polymarket-focused arbitrage bot scaffolding with high-performance ingestion, forward-looking storage, strategy engines (Dutch Book + Spread Capture), and robust test suite. Built for Windows + PowerShell + uv.

Quick Start
- `uv sync`
- `uv run pytest -q` (all green)

Core Commands
- Status: `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db` (add `--verbose` for quotes + timings)
- Mock WS: `uv run python -m polybot.cli mock-ws --port 9000`
- Ingest WS: `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
- Quoter WS (simulate): `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9000 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- Record WS: `uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 recordings/out.jsonl --max-messages 3 --subscribe`
- Quoter Replay: `uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
- Refresh Markets (Gamma): `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
- Run Service: `uv run python -m polybot.cli run-service --config config/markets.example.toml`
  - Use `[relayer].type = "fake"|"real"` in the TOML; `real` requires an injected client in code.
- Metrics: `uv run python -m polybot.cli metrics`
- Prometheus Export: `uv run python -m polybot.cli metrics-export`
- Metrics HTTP Server: `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 0`
- Status Top (diagnostics): `uv run python -m polybot.cli status-top --db-url sqlite:///./polybot.db --limit 10`
- Dutch (replay): `uv run python -m polybot.cli dutch-run-replay recordings/multi.jsonl mkt-1 --db-url sqlite:///./polybot.db --safety-margin-usdc 0.01 --fee-bps 20 --slippage-ticks 1`
- Relayer Dry Run: `uv run python -m polybot.cli relayer-dry-run mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x... --db-url sqlite:///./polybot.db`
  - (Prep) Allowances stubs: `relayer-approve-usdc` / `relayer-approve-outcome` print friendly messages until the real client is integrated.
- Telegram (offline runner): `uv run python -m polybot.cli tgbot-run-local updates.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
- Migrations: `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --print-sql` (or `--apply` if psycopg installed)
- DB Migrations: `uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --print-sql`
- Health: `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`

Docs
- PRD: `docs/prd.md`
- Technical Plan: `docs/technical-plan.md`
- Roadmap: `docs/roadmap.md`
- Deployment: `docs/deployment.md`
- Runbook: `docs/runbook.md`
- Acceptance: `docs/acceptance-checklist.md`, `docs/acceptance-walkthrough.md`

Notes
- Trading uses a FakeRelayer for safety in this phase. Wiring the real Polymarket relayer and CTF will follow.
- Put secrets in a gitignored TOML (e.g., `config/secrets.local.toml`); see `config/secrets.local.toml.example`.
