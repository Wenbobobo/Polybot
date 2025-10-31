# Deployment Guide (Phase 1: Polymarket-only)

This guide explains how to set up, run, and operate the Polybot MVP components on Windows with PowerShell and uv. It focuses on data ingestion, storage, strategy simulation, and local tooling. Trading against live relayers is not enabled yet in this phase.

## Prerequisites
- OS: Windows 10/11
- Python: 3.12 (uv will manage virtualenv automatically)
- PowerShell
- uv package manager

## Repository Setup
1. Clone the repo and open PowerShell in the project root.
2. Install dependencies:
   - `uv sync`
3. Verify test suite:
   - `uv run pytest -q`

## Configuration
- All configuration is file-based TOML. Defaults are in `config/default.toml`.
- Key sections (Phase 1):
  - `[polymarket]`: base URLs for Gamma (data) and Relayer (placeholder only at this phase).
  - `[db]`: SQLite URL (default `sqlite:///./polybot.db`) and WAL setting.
  - `[ingestion]`: buffer sizes, staleness thresholds, etc.
  - `[strategy]`: enable flags; DutchBook/Spread true by default.
  - `[thresholds]`: `min_profit_usdc = 0.02` preset for early simulations.
- Create a local override if needed:
  - Copy `config/default.toml` to `config/local.toml` (gitignored) and adjust values.

## Running Locally
### Replay Recorded Events
- Apply JSONL events (snapshot/delta) into the DB:
  - `uv run python -m polybot.cli replay recordings/sample.jsonl mkt-1 --db-url sqlite:///./polybot.db`

### WebSocket Ingestion (Mock or Real)
- With a local mock WS server:
  - `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 100`
- The ingestion runner resyncs on first-delta and sequence gaps by requesting a snapshot from a provider (fake in this phase).

### Check Status
- Show ingestion status per market:
  - `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db`

## Data Model & Retention
- SQLite (WAL) development database with tables:
  - `markets`, `outcomes`, `orderbook_events`, `orderbook_snapshots`, `orders`, `fills`, `market_status`, `exec_audit`.
- Manual snapshot and pruning utilities:
  - `OrderbookIngestor.persist_snapshot_now(ts_ms)`
  - `OrderbookIngestor.prune_events_before(ts_ms_threshold)`

## Strategies (Phase 1)
- Dutch Book (detector + planner only in tests).
- Spread Capture (planner + refresh policy + quoter with FakeRelayer for simulation).
- Execution engine persists orders/fills/audits to DB for traceability.

## Moving Toward Live Trading (Later Phases)
- Keys & Security:
  - Use `config/secrets.local.toml` for private keys (gitignored). Do not commit secrets.
  - Support EOA signing for Polymarket relayer when enabled.
- Allowances & On-chain Ops:
  - Before trading, set USDC allowance (and outcome token when needed) for Polymarket contracts.
  - Gas budgeting and CTF merge/split operations will be introduced in Conversions phase.
- Database:
  - Consider migrating to PostgreSQL (optionally with Timescale, pgvector). Connection string can replace SQLite in `[db]`.

## Observability
- JSON structured logs to stdout.
- Execution audit persisted in `exec_audit`.
- Planned: metrics and dashboards (Prometheus) in later phases.

## Runbooks & Ops Tips
- Ingestion appears stalled:
  - Check `market_status.last_update_ts_ms` and increase logging level.
  - Replay recent JSONL to debug state transitions.
- Storage growth:
  - Use pruning regularly; consider snapshots at intervals to reduce event volume.
- Testing:
  - `uv run pytest -q` should remain green before deployments.

## Known Limitations (MVP)
- WS protocol and payloads are generic in tests; real Polymarket subscriptions to be wired later.
- Relayer calls use a fake in tests; no live orders are sent in Phase 1.
- Telegram bot and external news feeds are deferred until data/storage/trading base is fully validated.

## Appendix: Example Local DB URLs
- SQLite file: `sqlite:///./polybot.db`
- SQLite in temp path: `sqlite:///C:/path/to/tmp/polybot.db`
- PostgreSQL (future): `postgresql://user:pass@host:5432/polybot`
