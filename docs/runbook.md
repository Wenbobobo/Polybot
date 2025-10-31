# Operations Runbook (Phase 1)

Note: This runbook covers day-to-day operations and troubleshooting. For installation and first-time setup, see `docs/deployment.md`.

This runbook covers common operational tasks for Polybot MVP in Phase 1.

## Health Checks
- Use `polybot.cli status` to view per-market ingestion status (last_seq, last_update_ts_ms, snapshots, deltas).
- Inspect logs (JSON) for `ingestion_resync_*` counters indicating resync events.
- Metrics:
  - `orders_placed`, `orders_filled`
  - `engine_execute_plan_ms_sum`, `engine_execute_plan_count`
  - `ingestion_msg_applied`, `ingestion_msg_invalid`
  - `ingestion_resync_first_delta`, `ingestion_resync_gap`, `ingestion_resync_checksum`

## Retention & Storage
- Periodic snapshots and event pruning run via the scheduler. For manual control:
  - `OrderbookIngestor.persist_snapshot_now(ts_ms)`
  - `OrderbookIngestor.prune_events_before(ts_ms_threshold)`
- Recommended thresholds (dev): snapshot every 30s, prune older than 5m for heavy streams.

## Replay & Diagnosis
- Replay a JSONL to reconstruct orderbooks and test strategy decisions:
  - `polybot.cli replay <file> <market_id> --db-url sqlite:///./polybot.db`
- Compare snapshots before/after deltas to validate checksum mismatches and resync behavior.
 - Validate message schemas using the pydantic models if needed (schemas.py).

## Quoting Lifecycle (Spread)
- The SpreadQuoter enforces:
  - Min requote interval
  - Movement-based refresh (tick/mid jump)
  - Inventory-aware sizing and cap enforcement
  - Cancel/replace threshold by side (≥ N ticks or size change)
  - Per-market rate limiting (token bucket)
- In DB:
  - `orders` shows current status; canceled from replace cadence.
  - `exec_audit` captures plan payloads, plan_id, and duration.

## Common Issues
- Frequent resyncs: check upstream WS order; increase buffer or adjust snapshot resync cadence.
- Storage bloat: ensure pruning interval and retention window are configured correctly.
- No quotes: verify staleness thresholds, requote interval, and movement triggers; check `market_status` freshness.

## Checklist Before Live Relayer Wiring
- All tests green.
- Ingestion health steady; resync counters low; snapshots periodic.
- SpreadQuoter shows predictable cancel/replace cadence under mock streams.
- Exec audits contain plan_id and structured intents/acks.
- Deployment guide steps verified on Windows + uv.
- Gamma markets refresh verified; markets/outcomes present in DB.
