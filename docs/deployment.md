# 部署指南（第一阶段：仅限 Polymarket）

本指南解释了如何在 Windows 环境中使用 PowerShell 和 uv 设置、运行并操作 Polybot MVP 组件。本阶段重点关注数据摄取、存储、策略模拟和本地工具。在此阶段中，尚未启用与实时中继器（relayer）进行交易的功能。

## 先决条件
- 操作系统：Windows 10/11
- Python 版本：3.12（uv 将自动管理虚拟环境）
- PowerShell
- uv 包管理器

## 仓库设置
1. 克隆仓库并在项目根目录中打开 PowerShell。
2. 安装依赖项：
   - `uv sync`
3. 验证测试套件：
   - `uv run pytest -q`

## 配置
- 所有配置都基于 TOML 文件。默认配置位于 `config/default.toml`。
- 关键部分（第一阶段）：
  - `[polymarket]`：Gamma（数据）和中继器（Relayer）的基础 URL（本阶段仅为占位）。
  - `[db]`：SQLite URL（默认为 `sqlite:///./polybot.db`）和 WAL 设置。
  - `[ingestion]`：缓冲区大小、过期阈值等。
  - `[strategy]`：启用标志；DutchBook/Spread 默认为 true。
  - `[thresholds]`：`min_profit_usdc = 0.02`，适用于早期模拟。
- 如有需要，可创建本地配置覆盖文件：
  - 将 `config/default.toml` 复制为 `config/local.toml`（该文件已被 git 忽略），并修改配置值。

## 本地运行
### 回放已记录事件
- 将 JSONL 事件（快照/增量）应用到数据库：
  - `uv run python -m polybot.cli replay recordings/sample.jsonl mkt-1 --db-url sqlite:///./polybot.db`

### WebSocket 摄取（模拟或真实）
- 使用本地模拟的 WebSocket 服务器：
  - `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 100`
- 摄取运行器会在首次增量和序列间隙时通过请求提供方快照来重新同步（本阶段为假数据）。

### 检查状态
- 查看各市场的摄取状态：
  - `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db`
  - 详细信息（报价 + 引擎耗时）：`uv run python -m polybot.cli status --db-url sqlite:///./polybot.db --verbose`

## 数据模型与保留策略
- 使用 SQLite（WAL 模式）开发数据库，包含以下表格：
  - `markets`, `outcomes`, `orderbook_events`, `orderbook_snapshots`, `orders`, `fills`, `market_status`, `exec_audit`。
- 手动快照与清理工具：
  - `OrderbookIngestor.persist_snapshot_now(ts_ms)`
  - `OrderbookIngestor.prune_events_before(ts_ms_threshold)`
  - 调度器支持：通过 `run_ingestion_session()` 实现周期性快照/清理。

## 策略（第一阶段）
- Dutch Book（仅在测试中包含检测器和规划器）。
- Spread Capture（规划器 + 刷新策略 + 使用 FakeRelayer 的报价器进行模拟）。
- 执行引擎将订单/成交/审计信息持久化到数据库以确保可追溯性。
  - 审计信息包括生成的 plan_id 和 measured duration_ms。

## 向实时交易迈进（后续阶段）
- 密钥与安全性：
  - 使用 `config/secrets.local.toml` 存储私钥（该文件已被 git 忽略）。请勿提交密钥。
  - 在启用后支持 EOA 签名以对接 Polymarket 中继器。
  - 对于服务配置（`run-service --config`），加载同目录下的 `secrets.local.toml` 并自动覆盖 `[relayer]` 字段（如 `private_key`、`dry_run`）。
- 授权与链上操作：
  - 交易前请为 Polymarket 合约设置 USDC 授权（必要时还需设置 outcome token）。
  - Gas 预算与 CTF 合并/拆分操作将在 Conversions 阶段引入。
- 数据库：
  - 可考虑迁移到 PostgreSQL（可选使用 Timescale、pgvector）。可在 `[db]` 中替换连接字符串。

## 可观测性
- JSON 结构化日志输出至 stdout。
- 执行审计信息保存在 `exec_audit` 中。
- 计划后续阶段引入指标和仪表板（Prometheus）。
 - 进程内指标：`uv run python -m polybot.cli metrics` 显示计数器（包括按市场标识的值）。
- Prometheus 暴露文本：`uv run python -m polybot.cli metrics-export` 可用于本地抓取或重定向至文件。
 - 轻量 HTTP 暴露：`uv run python -m polybot.cli metrics-serve --host 127.0.0.1 --port 0` 在本地提供 `/metrics`。

## 运行手册与操作提示
- 数据摄取出现停滞：
  - 检查 `market_status.last_update_ts_ms` 并提高日志级别。
  - 回放近期 JSONL 文件以调试状态变化。
- 存储增长：
  - 定期执行清理；可考虑按间隔保存快照以减少事件量。
- 测试：
  - 部署前确保 `uv run pytest -q` 仍能通过。

## 已知限制（MVP）
- 在测试中 WebSocket 协议和数据结构为通用格式；真实 Polymarket 订阅将在之后接入。
- 中继器调用在测试中使用 FakeRelayer；第一阶段不会发送真实订单。
- Telegram 机器人和外部新闻订阅将在数据/存储/交易基础完全验证后再引入。

## 数据库（PostgreSQL 路线）
- 配置中可将 `[db].url` 设置为 `postgresql://...`。当前版本会抛出清晰的 `NotImplementedError`（尚未接入驱动与迁移），用于在部署前进行配置验证。
- 未来版本将添加 PostgreSQL/Timescale 支持与索引/分区策略（见 `docs/handoff.md` 和 `docs/roadmap.md`）。

## 附录：示例本地数据库 URL
- SQLite 文件：`sqlite:///./polybot.db`
- SQLite 临时路径：`sqlite:///C:/path/to/tmp/polybot.db`
- PostgreSQL（未来）：`postgresql://user:pass@host:5432/polybot`
### 从事件流模拟 Spread 报价
- 使用 QuoterRunner（编程方式）消费事件流并使用 FakeRelayer 和内存数据库生成/取消报价。此功能用于离线验证报价生命周期前的行为。
- 如需生产环境模拟，可接入 WebSocket 客户端以生成订单簿消息，并在凭证/授权配置完成后使用真实中继器传递消息至 `QuoterRunner`。
### 刷新 Markets Catalog（Gamma）
- 一次性刷新到数据库：
  - `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
- 在代码中，使用 `GammaHttpClient` 调用 `polybot.ingestion.markets.refresh_markets` 实现周期性刷新。

### 对 WS 流运行 Spread Quoter
- 从类似 Polymarket 的 WebSocket 流模拟 Spread 报价（使用 FakeRelayer）：
  - `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9000 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 100`
- 注意事项：
  - 报价器会根据库存调整报价规模，并强制执行最小重报价间隔和风险敞口上限。
  - 后续阶段替换为真实中继器；确保授权和认证已配置。

### 运行多市场服务（模拟）
- 编程方式使用 ServiceRunner 并发执行多个市场任务：
  - 构造包含 `market_id`, `outcome_yes_id`, `ws_url`, `max_messages`, `subscribe=true` 的 MarketSpec 条目。
  - 初始化 `ServiceRunner(db_url)` 并调用 `await run_markets(specs)`。
- 此操作使用 FakeRelayer 模拟跨市场的并发订单簿消费与报价生成。

### 选择 Relayer 类型（为上线做准备）
- 在 `config/markets.example.toml` 中设置：
  - `[relayer] type = "fake"`（默认，安全模拟）
  - 未来接入真实中继器时设置为 `"real"` 并在代码中注入实际客户端（py-clob-client）。当前版本会在未注入客户端时抛出 `NotImplementedError`，避免误发单。
### 其他有用命令
- 快速诊断：`uv run python -m polybot.cli status-top --db-url sqlite:///./polybot.db --limit 10`
- 实盘干跑（需安装/配置 real relayer）：
  - `uv run python -m polybot.cli relayer-dry-run mkt-1 yes buy 0.40 1 --base-url https://clob.polymarket.com --private-key 0x... --db-url sqlite:///./polybot.db`
- tgbot 离线命令回放：
  - 准备 JSONL（每行一个 update，如 `{ "message": { "text": "/help" } }`）
  - `uv run python -m polybot.cli tgbot-run-local updates.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`

### 数据库迁移（PostgreSQL）
- 查看 SQL：`uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --print-sql`
- 应用迁移（需安装 psycopg）：`uv run python -m polybot.cli migrate --db-url postgresql://user:pass@host:5432/db --apply`
### （预备）授权 CLI（占位）
- 在接入真实客户端前，以下命令会输出友好的占位消息：
  - USDC 授权：`uv run python -m polybot.cli relayer-approve-usdc --base-url https://clob.polymarket.com --private-key 0x... --amount 100`
  - Outcome 授权：`uv run python -m polybot.cli relayer-approve-outcome --base-url https://clob.polymarket.com --private-key 0x... --token 0x... --amount 10`
