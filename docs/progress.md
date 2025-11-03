# Progress Log

This file tracks decisions and incremental progress.

2025-10-30
- Agreed scope: Polymarket-only, prioritize data+storage foundations.
- All config via TOML files; no env vars for required settings.
- Added docs (technical plan, roadmap, prd, progress) and AGENTS.md.
- Prepared project scaffold, tests blueprint, and default config template.

2025-10-31
- S1 complete: storage schema expanded (markets, outcomes, events, snapshots, orders, fills), recording JSONL utils, orderbook assembler.
- S2 complete: fake relayer and execution engine; integration tests.
- S3 complete: Dutch Book detector and planner with tests.
- S4 started and delivered MVP: Spread Capture planner with staleness guard and narrow-spread skip; execution with fake relayer.
- Added logging JSON formatter and SQLite WAL helper; tests pass.
- Added Gamma HTTP client with httpx and MockTransport-based unit tests (no external calls).
- Added orderbook replay harness and tests.
- Added WS client scaffold and tested against local Mock websockets server.
- Implemented ingestion worker that applies snapshots/deltas and persists to DB.
- Added ingestion runner with resync-on-first-delta and gap logic; tests cover resync.
- Introduced CLI (module) with subcommands: replay and ingest-ws; integration tests validate DB writes.
- Added market_status and exec_audit tables; execution engine now persists orders/fills and audits.
- Implemented spread refresh policy and a stateful SpreadQuoter; added tests.
- Added manual snapshot and pruning utilities; tests verify retention.
- Wrote deployment guide (docs/deployment.md) for Windows + uv.
- Added acceptance walkthrough (docs/acceptance-walkthrough.md) and README with quick commands.
- Implemented service runner and config; mock WS, record/replay tooling.
- Added per-market labelled metrics; status --verbose surfaces quote/order/engine timings.
- Quoter tuned: rate limiting, per-side replace thresholds/intervals, cancel throttling.
 - Gamma HTTP: pagination + tests；市场刷新调度：抖动+jitter与错误退避。
 - WS 翻译器：忽略非l2频道、支持data包裹与官方字段，严格schema校验；checksum匹配避免不必要重同步。
 - 执行引擎：幂等(plan_id+client_oid)、重试（可配置）；Prometheus 导出与HTTP服务。
- Postgres：提供基线迁移SQL与CLI打印；连接选择器清晰失败模式。
- S3 开始：DutchRunner（多Outcome聚合）+ CLI `dutch-run-replay`；tgbot 初版（离线命令解析+下单）。

2025-10-31 (cont.)
- S3 强化：
  - DutchRunner 支持从 DB 读取 outcomes 元信息（tick/min-size/name）、安全边际（fee_bps/slippage_ticks/safety_margin_usdc），并生成稳定 plan_id（基于 outcome seqs）确保幂等。
  - CLI：`dutch-run-replay` 增加 `--allow-other` 与 `--verbose`（输出 total_ask/margin/是否满足边际），自动 outcomes 读取与健壮性提示。
  - 规则变更守护：检测 markets.rule_hash 变更并跳过执行（dutch_rulehash_changed 指标）。
- Relayer：
  - CLI `relayer-dry-run` 支持通过“real” relayer 干跑单笔 IOC（默认 dry_run=true），用于真客户端联调验证；ServiceConfig 支持 relayer {type, base_url, dry_run, private_key}。
- Observability & Ops：
  - 新增 `status-top` 快速诊断（按重同步比率与取消限流排序），WS 元数据保留测试（market/ts_ms）。
  - Metrics：engine_place_ms_sum 与 engine_errors 标注下单耗时与失败。
- Migration：
  - `migrate --apply` 尝试在安装 psycopg 时直接应用 Postgres 迁移；未安装则返回清晰提示。

2025-11-01
- Relayer：`build_relayer("real")` 优先采用 PyClob 适配器（字段与幂等键映射一致）；保留通用适配回退。
- Engine：新增更细粒度计时指标（`engine_place_call_ms_sum/_count`，按市场标注）；原有执行计时保持。
- Service：`ServiceRunner` 增加任务异常防护与错误计数（`service_task_errors{market=...}`），并使用 `gather(..., return_exceptions=True)` 实现温和收敛。
- Postgres：迁移文件补充 `idx_orders_market_status` 索引以与 SQLite 索引对齐。
- Config：`run-service` 会读取同目录 `secrets.local.toml` 并覆盖 `[relayer]` 字段（如 `private_key`、`dry_run`）。
- CLI：新增授权占位命令 `relayer-approve-usdc` 与 `relayer-approve-outcome`（在未接入真实客户端时输出友好提示）。
- WS：WebSocket 客户端加入重连与重订阅（`max_reconnects`/`backoff_ms`），新增单测覆盖。
- PyClob 适配器：支持转发 `approve_usdc` 与 `approve_outcome` 至底层客户端（若提供）。
- Postgres：新增 Timescale 可选迁移脚本 `migrations/postgres/010_timescale.sql` 与单测覆盖；增加带 stub psycopg 的 `--apply` 烟雾测试。
- 订单簿：添加大快照用例以验证装配与最佳价提取在大数组下的稳健性。

2025-11-02
- Config 整合：仅保留 `config/service.example.toml` 与 `config/secrets.local.toml.example`；删除 `config/default.toml`、`config/markets.example.toml`、`config/live.example.toml`，测试迁移至临时配置文件。
- Observability：新增 Grafana 仪表板 `observability/grafana-dashboard.json`；`README` 增加 Grafana Quickstart。
- Relayer：
  - 包装器 `RetryRelayer`（place/cancel 重试 + 退避）；服务层暴露 `[service] relayer_max_retries/relayer_retry_sleep_ms`；
 - 取消指标：`relayer_cancel_count`、`relayer_cancel_ms_sum`；取消异常计数 `relayer_cancel_errors_total`；
  - 位置错误计数：`relayer_place_errors{market}`；应答指标扩充（accepted/rejected by status）。
- CLI/状态：`status-top` 增加 `place_errors` 列并按 resync_ratio→rejects→place_errors→cancel限流 排序。
- Allowance：CLI 计数增加 `relayer_allowance_success{kind}`；RelayerClient 暴露 `approve_usdc/approve_outcome`（snake/camel）。
- Spread（S4）完善：引入 `min_quote_lifetime_ms`、从 DB 读取 `tick_size` 以驱动 `min_change_ticks`、保留按侧替换窗口与取消限流；`status --verbose` 增加 cancel_rate_limited。
- Dutch（S3）已具备：多 outcome 汇总、规则哈希守护、费用/滑点/安全边际，稳定 plan_id 并计量 metrics（dutch_orders_placed / dutch_rulehash_changed）。
- 配置整合：引入单文件 `config/service.example.toml` + 机密覆盖；移除 `config/markets.example.toml` 与 `config/live.example.toml`（不再在文档中引用）。保留 `config/default.toml` 仅用于单元测试，后续将迁移测试后再移除。

- 小强化：
  - Real relayer 构造支持 `timeout_s` → `timeout` 归一化映射，提升与不同 py‑clob‑client 版本的兼容性（单测覆盖）。
  - 观测：`metrics-serve` 新增 `/health` 端点（200 ok），便于外部探针与容器健康检查（单测覆盖）。
  - Service：新增集成测试覆盖任务异常容错与 `service_task_errors{market}` 计数（坏连接不影响其他市场）。
  - Engine：新增 `engine_ack_ms_sum/_count`（per‑market），`status --verbose` 输出 `ack_avg_ms`。
  - Ingestion：`run_orderbook_stream` 支持按消息 `market` 字段过滤（仅处理目标市场），补充集成测试。
  - CLI：`status-top` 排序与列验证单测；Relayer allowances 命令重试/退避路径单测，`relayer_place_errors{market}` 异常计数单测。
  - Runner：长批量校验：连续正确 checksum 的增量流无重同步（集成测试）；取消重试 backoff 的休眠参数传递验证；服务每市场运行时长指标 `service_market_runtime_ms_sum/_count`。
  - Ingestion 重连：跨重连的 checksum 不匹配会触发受限重同步（指标验证），避免频繁拉取（节流已测）。
  - CLI：新增 `metrics-reset` 命令，用于测试/诊断时清空进程内计数器。
  - tgbot（S7 初版铺垫）：新增 webhook 服务器（HTTP /tg），按用户ID白名单拦截，请求体直接转发至 BotAgent；提供 `tgbot-serve` CLI（离线引擎）。
  - 执行审计：exec_audit 新增 place_call_ms 与 ack_latency_ms 字段（SQLite/Postgres），Engine 在可用时写入；保持旧 schema 回退兼容。
  - Relayer：对“速率限制”风格错误（429/包含 rate limit 文本）增加 `relayer_rate_limited_total` 计数；RetryRelayer place/cancel 路径均支持分类与退避单测。
  - WS：译器在大快照与字符串化数值下保持兼容，并保留官方元数据字段（market/channel/ts_ms）。
  - Exec 审计：新增 `request_id` 字段（SQLite/Postgres）；Engine 写入并保持旧列回退插入。
  - CLI：`status`/`status-summary`/`health` 支持 `--json` 输出；`status-summary` JSON 包含 `quotes_rate_limited` 与 `quotes_cancel_rate_limited`；`status-top` 增加全局 rate_limited/timeout 列；`audit-tail` 便于快速回溯。
  - WS 重连：正确校验和的分段流在重连下避免多余重同步（指标不增）。

2025-11-02 (cont.)
- CLI 改进：
  - `status --json --verbose` 现在在 JSON 中包含每市场的 `relayer_rate_limited_events` 与 `relayer_timeouts_events` 指标，便于仪表板与自动化诊断。
  - `relayer-live-order` 新增 `as_json` 输出选项（在 `--confirm-live` 生效前提下），返回 `{"placed":N,"accepted":M,"statuses":{...}}`，方便脚本化联调与回归。
- 测试：新增两项单测覆盖上述行为。

2025-11-03
- 目录与解析稳健性：
  - 新增 CLOB HTTP 客户端（`ClobHttpClient`）用于直接访问 `/markets` 与 `/markets/{id}`，降低构造差异与超时风险。
  - `markets-sync`：在 Gamma 返回缺少 condition_id 时自动回退到 CLOB 发现；加入分页与详情调用预算（`--clob-max-pages`、`--clob-details-limit`），避免长时间等待。
  - 解析器：`markets-resolve` 支持 HTTP 回退（无需详情调用，优先用 `clobTokenIds`），`--debug` 输出导入/构造/HTTP 回退信息。
  - Gamma 归一化：支持 `title=question|name|slug`，`market_id=condition_id|id|market_id|market`，`clobTokenIds` 与 `tokens` 的 outcome_id 映射。
- 诊断脚本：
  - 新增 `diag-markets` CLI：运行 Gamma-only 与 CLOB-HTTP 有界同步 + 解析调试，将结果写入指定日志文件，便于定位网络超时与字段错配问题。

Next (queued)
- py-clob-client 封装与 dry-run 联调（EOA 签名、拒单/超时/部分成交映射、速率控制/重试），完成后提醒配置钱包切实盘。
- S3 回放覆盖：临界边际、复杂 outcomes、规则变更大样本；CLI verbose 输出净边际分解（fee/slip/safety）。
- tgbot 正式化：接入 Telegram SDK/webhook，权限/白名单、二段确认（dry→confirm→live）、审计日志；支持触发 Dutch/Spread、状态与托管指令。
- 性能与观测：分段计时（下单/ack）、失败/拒单统计、DB 写路径与索引优化；WS→装配→策略链路热点优化。

Open Items (as of 2025-10-31)
- Wire real Polymarket relayer (py-clob-client), add idempotency keys, map rich OrderAck; document allowances and dry-run mode.
- Align WS translator and schemas with official Polymarket L2 payloads (channels, market filters, checksums); add fixtures and stricter validation.
- Prometheus exporter and dashboards; add metrics reset utilities for tests.
- Storage migration path to PostgreSQL/Timescale; add indices for frequent queries and bulk upsert helpers.
- Risk and circuit breaking: exposure caps across outcomes/markets, health/error/latency guards, order reject burst handling.
- Ops polish: reconnect/backoff, task watchdogs, graceful shutdowns; service runner health summaries.

Next Steps
- Prioritize relayer integration and WS schema alignment (S2/S1 hardening), then metrics exporter and Postgres migration.
- Expand SpreadParams tunables and batch cancel/replace logic; ensure tick-size-aware min_change thresholds.
- Extend CLI status --verbose with resync ratios and cancel rate-limit events; add quick "top offenders" view.
- S5 Conversions（预研完成）：新增 CTF 接口占位（merge/split）与简单的转换规划器（should_merge/should_split），含单测；暂不接入服务流，后续按真实客户端落地与费用模型细化。
# Progress Log
