# MVP Acceptance Checklist (Phase 1)

This checklist is used to verify readiness for MVP acceptance.

## Data & Ingestion
- [ ] Gamma normalization works (fixture-based), markets/outcomes persisted
- [ ] WS client connects and can send subscribe payload
- [ ] Runner applies snapshot/delta; resyncs on first-delta, gap, checksum mismatch
- [ ] Scheduler performs periodic snapshots and pruning; retention holds
- [ ] market_status reflects last_seq/last_update and counters

## Strategy & Execution
- [ ] Dutch Book detector + planner tested
- [ ] Spread Capture planner tested (staleness, spread width, mid-jump)
- [ ] SpreadQuoter enforces requote cadence, inventory-aware sizing, and inventory cap suppression
- [ ] Execution engine places orders, persists orders/fills, cancels by client_oid
- [ ] Exec audit writes plan_id, duration_ms, intents/acks JSON

## Observability & Ops
- [ ] JSON logging works; metrics counters increment
- [ ] CLI: replay, ingest-ws, status
- [ ] Runbook/delivery docs validated on Windows + uv

## Tests
- [ ] Unit + integration suites green locally via `uv run pytest -q`
- [ ] Recording/replay harness covers key paths

## Out of Scope (Phase 1)
- Live relayer orders (py-clob-client)
- CTF conversions; on-chain actions
- Telegram bot and external news feeds
