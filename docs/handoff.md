# Handoff Notes for Future Developers

Scope & Status
- Phase 1 MVP (Polymarket-only) implemented with:
  - High-performance ingestion (WS + snapshot/resync), event storage, and recording/replay
  - Strategies: Dutch Book (detector/planner + DutchRunner), Spread Capture (planner + quoter loop)
  - Execution engine with FakeRelayer; orders/fills/audits persisted; idempotency (plan_id + client_oid)
  - Observability: JSON logs, in-process metrics (labelled), status/health/status-top CLIs; Prometheus exporter + HTTP /metrics
  - Service runner for multi-market simulation; config supports default/per-market spread params；relayer config（type/base_url/dry_run/private_key）

What’s Next (Priority)
1) Wire real Polymarket relayer (py-clob-client)
   - DONE (Phase 1 wiring): `build_relayer("real")` now wraps injected or constructed py-clob client with `PyClobRelayer` (field mapping + idempotency). Falls back to generic adapter if unavailable.
   - NEXT: add EOA signer and allowances workflow before going live; provide CLI helpers and secrets file template.
   - Config: `[relayer]` in TOML stays default `fake` and `dry_run=true` for safety.

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
   - Baseline SQL is in `migrations/postgres/001_init.sql`; CLI exposes `migrate --print-sql` 与（安装 psycopg 时）`migrate --apply`。
   - Metrics exporter (Prometheus) and dashboards
   - Finer engine timings added (per-market): `engine_place_call_ms_sum/_count` alongside existing `engine_execute_plan_*` and `engine_place_ms_sum`.
   - Secrets management and environment profiles

S3 (Dutch Book) Notes
- 条件：sum(asks) < 1 - min_profit_usdc；可叠加 safety_margin_usdc + fee_bps + slippage_ticks。
- Runner：从 DB 读取 outcomes（tick/min/name），聚合 per-outcome 订单簿，生成稳定 plan_id；rule_hash 变更守护（跳过并计数）。
- 风控：执行前库存上限校验；Engine 幂等（plan_id + client_oid）；metrics 含 dutch_orders_placed 与 dutch_rulehash_changed。
- CLI：`dutch-run-replay`（支持 --allow-other/--verbose/自动 outcomes）；`status-top`（重同步/限流诊断）。

Relayer / Wallet & Secrets
- 不要提交私钥；将 `private_key` 放于 gitignored 的本地配置（如 `config/secrets.local.toml`）。`run-service --config <file>` 会自动读取同目录的 `secrets.local.toml` 并覆盖 `[relayer]` 字段。
- 切实盘前：
  - `[relayer]` 指向正确 base_url；dry_run=true 先联调；使用 `relayer-dry-run` 验证路径；
  - 完成 USDC 与 outcome token 授权（allowance）；目前提供占位 CLI：`relayer-approve-usdc` 与 `relayer-approve-outcome`（在未接入真实客户端时输出友好提示）。
  - 规则/市场风险过筛（避免 Other；核对 rule_hash）；
  - 合理的限速/重试参数，避免自我限流或风控触发。

Configuration Model (Consolidated)
- Use a single service config TOML (e.g., `config/service.example.toml`) containing `[service]`, `[service.spread]`, `[relayer]`, and `[[market]]` sections.
- Place a `secrets.local.toml` (gitignored) next to it to overlay `[relayer]` fields like `private_key` and `dry_run`.
- `run-service --config <path>` and `preflight/smoke-live` all read the same service config and apply the secrets overlay automatically.

Assistance Needed (from operator)
- Provide a dedicated wallet and private key (Polygon) in `config/secrets.local.toml` (never commit), and confirm `chain_id`.
- Install `py_clob_client` in the runtime environment and confirm constructor options (chain, timeout) if they differ.
- Confirm base URLs for CLOB and Gamma per environment (testnet/mainnet).
- When ready for live: run `preflight --config ...` then a single `relayer-dry-run` before enabling service.

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
- Diagnostics: `status`, `status --verbose`, `status-top`, `metrics[-export|-serve]`
- Strategy: `quoter-run-ws`, `quoter-run-replay`, `dutch-run-replay`
- Relayer: `relayer-dry-run`（真 relayer 干跑）
- Bot (offline): `tgbot-run-local`（/status、/buy、/sell）

Context Compression Tips
- 若对话上下文受限，请优先参考：`docs/roadmap.md`、`docs/technical-plan.md`、`docs/handoff.md`、`docs/progress.md` 与 `README.md`；
- 快速起步命令见 README；运维排障见 Runbook；验收流见 acceptance-walkthrough。

Contacts & Ownership
- Add ownership and secret distribution notes here when moving to live environments
