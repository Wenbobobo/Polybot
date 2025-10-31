# Progress Log

This file tracks decisions and incremental progress.

2025-10-30
- Agreed scope: Polymarket-only, prioritize data+storage foundations.
- All config via TOML files; no env vars for required settings.
- Added docs (technical plan, roadmap, prd, progress) and AGENTS.md.
- Prepared project scaffold, tests blueprint, and default config template.

2025-10-31
- S1 complete: storage schema expanded (markets, outcomes, events, snapshots, orders, fills), recording JSONL utils, orderbook assembler.
- S2 complete: fake relayer and execution engine; integration tests.
- S3 complete: Dutch Book detector and planner with tests.
- S4 started and delivered MVP: Spread Capture planner with staleness guard and narrow-spread skip; execution with fake relayer.
- Added logging JSON formatter and SQLite WAL helper; tests pass.
- Added Gamma HTTP client with httpx and MockTransport-based unit tests (no external calls).
- Added orderbook replay harness and tests.
- Added WS client scaffold and tested against local Mock websockets server.
- Implemented ingestion worker that applies snapshots/deltas and persists to DB.
- Added ingestion runner with resync-on-first-delta and gap logic; tests cover resync.
- Introduced CLI (module) with subcommands: replay and ingest-ws; integration tests validate DB writes.
- Added market_status and exec_audit tables; execution engine now persists orders/fills and audits.
- Implemented spread refresh policy and a stateful SpreadQuoter; added tests.
- Added manual snapshot and pruning utilities; tests verify retention.
- Wrote deployment guide (docs/deployment.md) for Windows + uv.
- Added acceptance walkthrough (docs/acceptance-walkthrough.md) and README with quick commands.
- Implemented service runner and config; mock WS, record/replay tooling.
- Added per-market labelled metrics; status --verbose surfaces quote/order/engine timings.
- Quoter tuned: rate limiting, per-side replace thresholds/intervals, cancel throttling.

Open Items (as of 2025-10-31)
- Wire real Polymarket relayer (py-clob-client), add idempotency keys, map rich OrderAck; document allowances and dry-run mode.
- Align WS translator and schemas with official Polymarket L2 payloads (channels, market filters, checksums); add fixtures and stricter validation.
- Prometheus exporter and dashboards; add metrics reset utilities for tests.
- Storage migration path to PostgreSQL/Timescale; add indices for frequent queries and bulk upsert helpers.
- Risk and circuit breaking: exposure caps across outcomes/markets, health/error/latency guards, order reject burst handling.
- Ops polish: reconnect/backoff, task watchdogs, graceful shutdowns; service runner health summaries.

Next Steps
- Prioritize relayer integration and WS schema alignment (S2/S1 hardening), then metrics exporter and Postgres migration.
- Expand SpreadParams tunables and batch cancel/replace logic; ensure tick-size-aware min_change thresholds.
- Extend CLI status --verbose with resync ratios and cancel rate-limit events; add quick "top offenders" view.
