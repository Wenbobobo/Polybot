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
- Detector: sum(outcomes) < 1, tick/min-size/rule checks（避免Other）
- Planner: 批量IOC下单；未来纳入费用/滑点（gas/fee）估计
- Runner: 多Outcome订单簿聚合（DutchRunner），从消息流触发检测并执行
- CLI: `dutch-run-replay` 从JSONL回放多Outcome消息
- TDD: 回放与确定性利润校验；风控（库存上限、幂等）

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
- Surface builder allowance / funding metrics inside `status-top`, Grafana, and smoke scripts so live readiness is continuously visible.

## S7 Telegram Bot (post S2)
- Alerts, status, optional approvals
- Config and permissions model；托管下单（类似 gmgnbot）
- 初版：离线命令解析与引擎联动（不依赖网络），后续接入 Telegram SDK 与权限校验
- Draft full PRD/interaction spec (`docs/tgbot-prd.md`) covering market lookup → risk gates → confirm/close UX before writing code.

## Queued Next (post S1–S4)
- Real relayer (py‑clob‑client) live wiring: signer, timeouts/backoff, allowance calls, richer acks.
- WS: additional official checksum fixtures and extreme cases; persistent streams; ping/pong.
- CTF (S5 prod): real client for merge/split with gas/fee models; risk gates; CLI and service integration.
- Dashboards: Prometheus scraping and Grafana baseline.
