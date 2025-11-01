# MVP 验收流程（第一阶段）

本指南将逐步介绍如何使用 Windows + PowerShell + uv 的内置工具和命令验证 `docs/acceptance-checklist.md` 中的每一项内容。

## 0) 环境设置
- 安装依赖：`uv sync`
- 运行测试：`uv run pytest -q`（应为绿色通过）

## 1) 数据与摄取
- Gamma 归一化与数据库更新：
  - `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
  - 验证数据行：启动摄取后 `status` 应显示市场信息（此步骤可选）。
- WS 客户端 + 订阅 + 转换：
  - 启动模拟 WS：`uv run python -m polybot.cli mock-ws --port 9000`
  - 摄取数据：`uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
  - 查看状态：`uv run python -m polybot.cli status --db-url sqlite:///./polybot.db --verbose`
  - 验证 applied/invalid 计数器；last_update_ts_ms 是否更新；snapshots/deltas 是否大于 0。
- 调度器（可选实时检查）：
  - 查看 `run_ingestion_session` 和 `market_scheduler` 的测试，了解定期快照与清理功能。

## 2) 策略与执行
- Dutch Book 检测与规划：由测试覆盖；参见 `tests/unit/test_dutch_book.py` 和 `tests/integration/test_dutch_book_execution.py`。
- Spread Capture 规划器与报价器：
  - 回放演示：`uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
  - 验证数据库中的订单：`SELECT COUNT(*) FROM orders;` > 0
  - 使用模拟的 WS 演示：
    - `uv run python -m polybot.cli mock-ws --port 9001`
    - `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9001 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- 执行与持久化：
  - 执行审计：`SELECT * FROM exec_audit ORDER BY id DESC LIMIT 1;` 包含 plan_id，duration_ms，以及 intents/acks JSON 数据。
  - 订单与成交表已填充；报价被替换时，取消订单应出现。

## 3) 可观测性与运维
- 默认情况下，JSON 日志会打印到 stdout。
- 指标：
  - `uv run python -m polybot.cli metrics` 打印计数器，包括按市场标记的值。
  - `status --verbose` 显示每个市场的报价与引擎耗时（平均毫秒数和次数）。
- 健康检查：
  - `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`
  - 调整 staleness 阈值以模拟过期状态。

## 4) 服务编排（模拟）
- 创建一个服务配置（或使用 `config/service.example.toml` 作为模板）。
- 启动模拟 WS 服务：`uv run python -m polybot.cli mock-ws --port 9002`
- 运行服务：`uv run python -m polybot.cli run-service --config config/service.example.toml`
- 验证订单与审计记录已写入；`status --verbose` 显示活动信息。

## 5) 记录与回放
- 记录：`uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 out.jsonl --max-messages 3 --subscribe`
- 回放：`uv run python -m polybot.cli quoter-run-replay out.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`

## 6) 注意事项与后续步骤
- 当前 MVP 的执行是离线/模拟的（使用 FakeRelayer）。下一步将接入真实的 relayer（py-clob-client）、CTF 和 Polymarket 的真实 WS 数据。
- 所有必要的验收项均通过测试和上述命令进行了覆盖。
