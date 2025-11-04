# Handoff Notes for Future Developers

Scope & Status
- Phase 1 MVP (Polymarket-only) implemented with:
  - High-performance ingestion (WS + snapshot/resync), event storage, and recording/replay
  - Strategies: Dutch Book (detector/planner + DutchRunner), Spread Capture (planner + quoter loop)
  - Execution engine with FakeRelayer; orders/fills/audits persisted; idempotency (plan_id + client_oid)
  - Observability: JSON logs, in-process metrics (labelled), status/health/status-top CLIs; Prometheus exporter + HTTP /metrics
- Service runner for multi-market simulation; config supports default/per-market spread params；relayer config（type/base_url/dry_run/private_key）
  - Real relayer wiring now auto-wraps py-clob-client instances (bridging `create_order`/`post_orders` to our adapter and forwarding timeout/chain_id aliases); CLI resolve flow gains Next.js (`__NEXT_DATA__`) fallback for modern market slugs. Live smoke validated with a 0.39 buy / 0.37 sell (size 5) on market `0x1fbeca9…`.

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
  - 安装 `py-clob-client`：使用 uv 安装（`uv add py-clob-client`），或 `uv pip install py-clob-client`；保持 `dry_run=true` 进行首次联调。

Configuration Model (Consolidated)
- Use a single service config TOML (e.g., `config/service.example.toml`) containing `[service]`, `[service.spread]`, `[relayer]`, and `[[market]]` sections.
- Place a `secrets.local.toml` (gitignored) next to it to overlay `[relayer]` fields like `private_key` and `dry_run`.
- `run-service --config <path>` and `preflight/smoke-live` all read the same service config and apply the secrets overlay automatically.

Live Wiring Checklist (for operators)
- 安装 `py-clob-client` 并确认版本；
- 更新 `secrets.local.toml`（Polygon 私钥，`dry_run=true` 初次）；
- `preflight --config ...` → `smoke-live`（dry-run）→ `status --verbose` 与 Grafana 仪表板观察；
- 确认后再将 `dry_run=false`，充值 USDC 并执行最小额度订单（严格监控风控与指标）。

Assistance Needed (from operator)
- Provide a dedicated wallet and private key (Polygon) in `config/secrets.local.toml` (never commit), and confirm `chain_id`.

Current State Snapshot (2025-11)
- Ingestion: robust WS snapshot/delta + resync (first-delta, gap, checksum); reconnect with optional throttled snapshot; translator accepts official-like payloads (l2, data-wrapped, metadata fields) and large snapshots.
- Storage: SQLite WAL baseline; Postgres DDL present (optional Timescale). Tables include markets/outcomes/events/snapshots/orders/fills/market_status/exec_audit.
- Execution: idempotency (plan_id + client_order_id); retry wrapper; audit persisted with timings (duration_ms, place_call_ms, ack_latency_ms) and request_id (fallback-safe if columns absent).
- Relayer: FakeRelayer for safety; real path via PyClob adapter; classification metrics for retries (global and per-market).
- Strategies: Dutch Book + Spread (inventory-aware, rate/cancel limits, min quote lifetime, tick-size aware).
- Observability: in-process metrics; Prometheus text exporter; HTTP server with `/metrics`, `/health`, `/status` (JSON of counters); CLI diagnostics (status/status-top/status-summary with JSON options); audit-tail (text/JSON).
- Tooling: orders-tail (text/JSON), orders-cancel by client_oid; config-dump (redacted JSON); metrics-json.
- tgbot: offline webhook server + CLI tgbot-serve (whitelist) built on FakeRelayer.

Operator Quickstart (dev)
- Run tests: `uv sync && uv run pytest -q`.
- Explore metrics: `uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 8000` (GET `/metrics`, `/health`, `/status`).
- Status & summary: `status --db-url ... [--verbose|--json]`, `status-summary --db-url ... [--json]`, `status-top --json`.
- Exec audit and orders: `audit-tail --db-url ... [--json]`, `orders-tail --db-url ... [--json]`, `orders-cancel c1,c2 --relayer fake`.
- Service: `run-service --config config/service.toml [--summary-json-output out.json]`.

Live Wiring Checklist (real relayer)
- Ensure `py-clob-client` installed and secrets present in `config/secrets.local.toml` (`[relayer] private_key="0x..."`, `dry_run=false`, correct `chain_id`).
- Preflight: `preflight --config ... [--json]`.
- Live safety flow: start with `smoke-live` (dry-run call) to validate signer/client; then a guarded `relayer-live-order --confirm-live` at tiny size.
- Watch metrics: `relayer_rate_limited_total`, `relayer_timeouts_total`; per-market `relayer_rate_limited_events{market}`, `relayer_timeouts_events{market}`.
- Verify audit: `audit-tail --db-url ...` (check timings, request_id) and DB `orders/fills` as expected.

Priorities (next)
- Relayer E2E hardening: allowances/timeout/rate-limit behaviors; duplicate plan idempotency verification on real path; consider JSON output for `relayer-live-order`.
- WS protocol: expand official-shaped reconnect/partial checksum sequences and large bursts; keep translator backward-compatible.
- Service ops: include per-market relayer event counts in summary; improve graceful teardown and health reporting.
- Postgres: optional `migrate --apply` verification under psycopg; Timescale optional.
- Observability & dashboards: consider histogram-like metrics for timings; extend dashboard panels (quotes/latencies/relayer classifications).

Safety & Ops Notes
- Never commit secrets; rely on TOML files with secrets overlay (gitignored). Keep `dry_run=true` until real paths are validated via smoke tests.
- Prefer Windows + PowerShell + uv commands already documented in README/commands-reference.
- Metrics are in-process; tests reset counters when needed (`metrics-reset`, or programmatic `metrics.reset()`).
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

JSON Outputs
- `status --json --verbose` 包含每市场的重同步比率、报价限流计数，以及新增的 `relayer_rate_limited_events` 与 `relayer_timeouts_events` 用于可视化与报警。
- `relayer-live-order` 支持 `as_json`（需 `--confirm-live`），用于自动化联调/回归测试（返回下单与状态分布统计）。

Diagnostics & Market Sync
- 当 Gamma `/markets` 返回旧样本或缺少 `condition_id` 时，使用 CLOB 路径：
  - 快速同步：`markets-sync --once --clob-max-pages 1 --clob-details-limit 0`（优先用 `/markets` 的 `clobTokenIds`，避免详情调用）
  - 如需更完整 token，适度提高 `--clob-details-limit`（会增加时长）。
- 解析：`markets-resolve --url ... --json --debug` 支持 HTTP 回退；`debug` 中的 `attempted_ids` 可用于定位 404 的 condition_id。
- 诊断脚本：`diag-markets --out-file recordings/diag.txt --url ...` 顺序执行 Gamma-only、CLOB-HTTP 有界同步与解析，将输出写入日志文件供排错。

Context Compression Tips
- 若对话上下文受限，请优先参考：`docs/roadmap.md`、`docs/technical-plan.md`、`docs/handoff.md`、`docs/progress.md` 与 `README.md`；
- 快速起步命令见 README；运维排障见 Runbook；验收流见 acceptance-walkthrough。

Contacts & Ownership
- Add ownership and secret distribution notes here when moving to live environments
