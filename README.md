Polybot (Phase 1 MVP)
=====================

Polymarket-focused arbitrage bot scaffolding with high-performance ingestion, forward-looking storage, strategy engines (Dutch Book + Spread Capture), and robust test suite. Built for Windows + PowerShell + uv.

Quick Start
- `uv sync`
- `uv run pytest -q` (all green)

Config Guide
- Single service file: `config/service.example.toml` (copy to `config/service.toml` and edit)
- Secrets overlay (gitignored): `config/secrets.local.toml` next to your service file
- Loader behavior: the service loader reads your service file and overlays any `[relayer]` fields found in `secrets.local.toml`
- Minimal secrets overlay example:
  - `[relayer] private_key = "0x..."`, `dry_run = false`, `chain_id = 137`

Core Commands
- Status: `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db` (add `--verbose` for quotes + timings)
- Mock WS: `uv run python -m polybot.cli mock-ws --port 9000`
- Ingest WS: `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
- Quoter WS (simulate): `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9000 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- Record WS: `uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 recordings/out.jsonl --max-messages 3 --subscribe`
- Quoter Replay: `uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
- Refresh Markets (Gamma): `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
- Run Service: `uv run python -m polybot.cli run-service --config config/service.example.toml`
  - Use `[relayer].type = "fake"|"real"` in the TOML; `real` requires py-clob-client and a private key via secrets overlay.
  - Retry controls: `[service] relayer_max_retries`, `relayer_retry_sleep_ms`; engine-level: `engine_max_retries`, `engine_retry_sleep_ms`.
  - Validate config before live: `uv run python -m polybot.cli preflight --config config/service.example.toml`
- Metrics: `uv run python -m polybot.cli metrics`
- Prometheus Export: `uv run python -m polybot.cli metrics-export`
- Metrics HTTP Server: `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 0`
- Grafana Dashboard: import `observability/grafana-dashboard.json` and point it at your Prometheus datasource.

Grafana Quickstart
- Run the metrics HTTP server locally: `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 8000`
- Point Prometheus at `http://127.0.0.1:8000/metrics` (scrape job in your prometheus.yml)
- Import `observability/grafana-dashboard.json` into Grafana and select your Prometheus datasource
- Status Top (diagnostics): `uv run python -m polybot.cli status-top --db-url sqlite:///./polybot.db --limit 10`
- Dutch (replay): `uv run python -m polybot.cli dutch-run-replay recordings/multi.jsonl mkt-1 --db-url sqlite:///./polybot.db --safety-margin-usdc 0.01 --fee-bps 20 --slippage-ticks 1`
- Relayer Dry Run: `uv run python -m polybot.cli relayer-dry-run mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x... --db-url sqlite:///./polybot.db`
  - (Prep) Allowances stubs: `relayer-approve-usdc` / `relayer-approve-outcome` print friendly messages until the real client is integrated.
  - Preflight config checks before live: `uv run python -m polybot.cli preflight --config config/service.example.toml`
  - Live smoke check (preflight + dry-run): `uv run python -m polybot.cli smoke-live --config config/service.example.toml mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x...`
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
 - For the service engine, you can control retries/backoff via `[service] engine_max_retries` and `engine_retry_sleep_ms` in your config.

System Overview

```mermaid
flowchart LR
  subgraph Data
    WS[Polymarket WS L2] -->|snapshot/delta| Translator
    Gamma[Gamma HTTP] --> Markets
  end
  Translator --> Ingestor
  Ingestor --> DB[(SQLite/Postgres)]
  Markets --> DB
  DB --> Strategies
  subgraph Strategies
    Dutch[\nDutch Book\n]
    Spread[\nSpread Capture\n]
  end
  Strategies --> Engine
  Engine --> Relayer[Relayer (fake/real)]
  Engine --> Audit[Exec Audit]
  Audit --> DB
  Engine --> Metrics[Metrics]
  Ingestor --> Metrics
```

Component Architecture

```mermaid
flowchart TB
  subgraph Ingestion
    T[Translator] --> V[Validator]
    V --> A[Assembler]
    A --> S[Snapshot/Events]
  end
  S --> DB[(DB)]
  DB --> DRunner[DutchRunner]
  DB --> QRunner[QuoterRunner]
  DRunner --> Eng[ExecutionEngine]
  QRunner --> Eng
  Eng --> Rel[Relayer]
  Eng --> EA[Exec Audit]
  EA --> DB
```
