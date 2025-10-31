# Handoff Notes for Future Developers

Scope & Status
- Phase 1 MVP (Polymarket-only) implemented with:
  - High-performance ingestion (WS + snapshot/resync), event storage, and recording/replay
  - Strategies: Dutch Book (detector/planner), Spread Capture (planner + quoter loop)
  - Execution engine with FakeRelayer; orders/fills/audits persisted
  - Observability: JSON logs, in-process metrics (labelled), status/health CLIs
  - Service runner for multi-market simulation; config supports default and per-market spread params

What’s Next (Priority)
1) Wire real Polymarket relayer (py-clob-client)
   - Adapter provided: `RelayerClient` (in code) accepts an injected client with `place_orders`/`cancel_orders`.
   - Config wiring: Service config reads `[relayer].type = "fake|real"`; runner builds relayer via `build_relayer`. Default remains `fake` for safety.
   - Engine passes `plan_id` as `idempotency_prefix` when available. `PyClobRelayer` adapter exists to wrap py-clob-client and map fields; add EOA signer when moving to live.
   - Implement order placement/cancel with idempotency keys and map Acks into our OrderAck
   - Allowances: add CLI to approve USDC and outcome tokens on Polygon; carefully isolate keys via config/secrets files
   - Add dry-run mode and per-env config (test/live)

2) WS protocol alignment
   - Extended: schemas and translator accept `channel`, `market`, `ts_ms`, and wrapped `data`. Translator ignores non-`l2` channels. Next: finalize checksum semantics and per-market filters with official fixtures.
   - Support per-market subscribe and reconnection strategies; backpressure handling
   - Expand validator schemas to match official payloads; add fixtures

3) Risk & Controls
   - Extend exposure caps across outcomes and markets; add notional caps
   - Add circuit breakers: repeated failures, latency spikes, order reject bursts
   - Persist per-market state to DB for resumable state

4) Storage & Infra
   - PostgreSQL migration (optionally Timescale); add indices/partitions per observed access patterns
   - Baseline SQL is in `migrations/postgres/001_init.sql`; CLI exposes `migrate --print-sql`.
   - Metrics exporter (Prometheus) and dashboards
   - Secrets management and environment profiles

File-level TODOs (for quick pickup)
- adapters/polymarket/ws_translator.py: implement exact field mapping for official L2 payloads (channels, market filters) and checksum semantics; keep translate_polymarket_message backward-compatible.
- adapters/polymarket/schemas.py: extend SnapshotMsg/DeltaMsg to official schema fields (channel, market, timestamps, nested arrays) and add stricter validation of nested arrays.
- adapters/polymarket/gamma_http.py: align endpoint path/query params to official Gamma spec and pagination; extend unit tests with additional fixtures.
- adapters/polymarket/relayer.py: add real RelayerClient (py-clob-client) alongside FakeRelayer; introduce idempotency keys and richer OrderAck mapping.
- strategy/spread_quoter.py: integrate batch cancel/replace per-side window; enforce min_change_ticks using exchange tick sizes from market metadata; add smarter pricing guardrails.
- strategy/spread.py: expose more tunables in SpreadParams (e.g., max cancels per minute per market, min quote lifetime).
- ingestion/runner.py: add reconnect/backoff and snapshot throttling; surface resync reasons to logs with plan_id/req_id correlation.
- service/runner.py: add task health monitoring, exception fencing, graceful teardown; optional per-market metrics summary on stop.
- ingestion/markets.py & ingestion/market_scheduler.py: add jitter to refresh interval; handle Gamma errors/backoffs.
- exec/engine.py: attach per-plan request IDs; integrate idempotency; persist engine timing breakdown (placement, ack latency) to exec_audit.
- storage/orders.py: add bulk upsert helpers for batched acks and DB indices for frequent queries (market_id, status).
- observability/metrics.py: add reset utilities for tests and Prometheus exporter module; consider histograms for engine timings.
- cli/commands.py: extend status --verbose to include per-market resync ratios and cancel rate-limit events; add a "top offenders" quick view.
- config/default.toml: relayer/gamma URLs are placeholders; add config/secrets.local.toml examples for keys (never commit secrets).

Dev Practices
- TDD-first; add fixtures and fakes for network-dependent code
- Keep CLI lean and scriptable for ops (status/metrics/health)
- Update docs: runbook, deployment, and acceptance checklist with every major change

Gotchas
- Don’t place live orders until py-clob-client integration is thoroughly dry-run tested
- Polymarket rules/neg-risk: avoid ‘Other’ outcome; read rule hashes
- Ensure cancel/replace and rate limits are tuned to avoid spam

Key Commands
- See README and docs/acceptance-walkthrough.md for end-to-end steps

Contacts & Ownership
- Add ownership and secret distribution notes here when moving to live environments
