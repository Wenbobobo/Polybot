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
   - Add a new adapter: RelayerClient using py-clob-client (EOA signer)
   - Implement order placement/cancel with idempotency keys and map Acks into our OrderAck
   - Allowances: add CLI to approve USDC and outcome tokens on Polygon; carefully isolate keys via config/secrets files
   - Add dry-run mode and per-env config (test/live)

2) WS protocol alignment
   - Replace ws_translator with exact Polymarket L2 schema (channels, market filters, checksums)
   - Support per-market subscribe and reconnection strategies; backpressure handling
   - Expand validator schemas to match official payloads; add fixtures

3) Risk & Controls
   - Extend exposure caps across outcomes and markets; add notional caps
   - Add circuit breakers: repeated failures, latency spikes, order reject bursts
   - Persist per-market state to DB for resumable state

4) Storage & Infra
   - PostgreSQL migration (optionally Timescale); add indices/partitions per observed access patterns
   - Metrics exporter (Prometheus) and dashboards
   - Secrets management and environment profiles

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
