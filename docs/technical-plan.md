# Technical Plan (Polymarket-only, Phase 1)

This document tracks the technical solution for the Polymarket arbitrage bot with emphasis on high-performance data ingestion, forward-looking database design, and TDD.

Scope
- Only Polymarket: Gamma (REST), Orderbook (WS), Relayer (orders), CTF (merge/split).
- Strategies by priority: Dutch Book, Bid-Ask Spread Capture; Conversions later; News/sweeping deferred.
- Config via TOML files; no environment variables for required settings.

Architecture Overview
- adapters/polymarket: GammaClient, OrderbookWS, RelayerClient, CTFClient.
- core: domain models, price/odds math, fee/gas/slippage calculators, risk checks.
- exec: opportunity detection, execution planning, two-phase order flow.
- storage: event-sourced schema (orderbook events, trades, our orders/fills), snapshots, indices/partitions.
- observability: structured logs, metrics, recordings (record/replay).

Data Ingestion
- WS-first for real-time L2; REST for snapshots and resync.
- WS client scaffold uses generic JSON messages for tests; Polymarket subscription semantics to be added when wiring live.
- Snapshot→delta with monotonic seq; gap detection and partial resync.
- Backpressure and batching; per-market freshness (age_ms) and health.

Database (dev→prod)
- Dev: SQLite (WAL). Prod: PostgreSQL (Timescale/pgvector optional later). RedisBloom/DuckDB are optional tooling.
- Core tables: markets, outcomes, orderbook_events, trades, snapshots, orders, fills, positions.
- Indices: (market_id, ts), (market_id, seq), (market_id, side, price).
- Retention: raw events 7–14d (compressed offline), snapshots 7d, aggregates long-term.

Execution & Risk
- IOC/FOK/limit; partial-fill handling and cancel/replace.
- Health gates and circuit breakers; staleness thresholds; min_profit_usdc default 0.02.
- Neg-risk/Other safeguards; rule hash watch.

Testing (TDD)
- Unit: math, book assembly, staleness, schema utilities, config loader.
- Integration: fake WS/REST, snapshot/delta reorder/drop, partial fills, batch cancel.
- Replay: recorded streams → deterministic verification.

Performance Targets (initial)
- Median delta-apply latency < 20ms per market; ≥5k L2 changes/min total; resync < 300ms.

Open Items (tracked in roadmap)
- Exact WS/REST payload schemas; relayer FOK/IOC semantics; CTF gas models.
