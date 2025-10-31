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
  - metrics: per-market counters and timers; status surfaces applied/invalid/resync/quotes and engine timings.

Data Ingestion
- WS-first for real-time L2; REST for snapshots and resync.
- WS client scaffold uses generic JSON messages for tests; Polymarket subscription semantics to be added when wiring live.
- Snapshot→delta with monotonic seq; gap detection and partial resync.
- Backpressure and batching; per-market freshness (age_ms) and health.
 - Message validation (pydantic), checksum checks, metrics counters for invalid/applied and resync reasons.

Markets Catalog
- Periodic refresh via Gamma HTTP client; normalize and upsert into DB (markets/outcomes).
- Scheduler hook to keep catalog current for strategy filters.

Database (dev→prod)
- Dev: SQLite (WAL). Prod: PostgreSQL (Timescale/pgvector optional later). RedisBloom/DuckDB are optional tooling.
- Core tables: markets, outcomes, orderbook_events, trades, snapshots, orders, fills, positions.
- Indices: (market_id, ts), (market_id, seq), (market_id, side, price).
- Retention: raw events 7–14d (compressed offline), snapshots 7d, aggregates long-term.

Execution & Risk
- IOC/FOK/limit; partial-fill handling and cancel/replace.
- Health gates and circuit breakers; staleness thresholds; min_profit_usdc default 0.02.
- Neg-risk/Other safeguards; rule hash watch.
- Exposure guard: compute inventory from fills; cap per outcome; drop intents that breach cap.
 - Cancel/replace policy: only replace sides when price change ≥ N ticks or size changed; per-market rate limiting.

Testing (TDD)
- Unit: math, book assembly, staleness, schema utilities, config loader.
- Integration: fake WS/REST, snapshot/delta reorder/drop, partial fills, batch cancel.
- Replay: recorded streams → deterministic verification.

Performance Targets (initial)
- Median delta-apply latency < 20ms per market; ≥5k L2 changes/min total; resync < 300ms.

Open Items (tracked in roadmap)
- Exact WS/REST payload schemas; relayer FOK/IOC semantics; CTF gas models.

Dutch Book (S3) Design Notes
- Input: 聚合一个市场的多Outcome最佳卖价；若 sum(asks) < 1 - min_profit_usdc，则触发。
- Runner: `DutchRunner` 维护 outcome->orderbook 汇总，周期性构造 MarketQuotes 并调用 planner 生成 IOC 方案。
- 幂等与风险：通过 ExecutionEngine 的 plan_id + client_oid 控制幂等，下单前用 `will_exceed_exposure` 校验库存上限。
- 扩展：后续结合 rule_hash 检查、避免 Other、最小成交规模与Tick对齐；引入费用/滑点安全边际。

Telegram 托管下单（预研）
- 初版：`tgbot` 模块提供命令解析与引擎联动（/status、/buy、/sell、/arb），离线可测；
- 正式版：接入官方 SDK 与 webhook，权限/白名单、最小下单额、确认流程（dry-run→确认→实盘），日志与审计。
