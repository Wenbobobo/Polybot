# Roadmap (Polymarket-only)

## S1 Data & Storage Foundation
- Gamma fetcher (markets index), selection rules
- Orderbook WS: snapshot+delta, seq validation, resync
- Storage schema: events, snapshots, markets/outcomes (SQLite WAL)
- Recording/replay tool scaffolding
- TDD: orderbook assembly, staleness, schema creation

## S2 Trading Foundation
- Relayer client: sign/place/cancel/batch; status
- Execution engine: IOC/FOK, partial-fill handling, retries
- Risk: health/staleness/circuit breakers, min_profit_usdc
- TDD: order API contracts, failure/retry, audit logging

## S3 Strategy: Dutch Book
- Detector: sum(outcomes) < 1, tick/min-size/rule checks
- Planner: batch orders; profit check incl. gas
- TDD: replay and deterministic profit validation

## S4 Strategy: Spread Capture
- Two-sided quoting, dynamic spread, inventory symmetry
- Pull on volatility/staleness; cooldowns
- TDD: quote update policies and cancel/replace

## S5 (Deferred) Conversions
- CTF merge/split workflow, gas thresholds, approvals
- TDD: merge happy-path + failure handling

## S6 Observability & Hardening
- Metrics, dashboards, performance tuning
- Regression suite from recordings; documentation polish

## S7 Telegram Bot (post S2)
- Alerts, status, optional approvals
- Config and permissions model
