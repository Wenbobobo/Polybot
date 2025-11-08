# 部署指南

本文提供可操作的“最短路径”部署流程，其余详细命令已迁移到《命令大全》（docs/commands-reference.md）。假设你在 Windows + PowerShell 环境中使用 uv。

---

## 1. 环境准备
| 步骤 | 指令 |
| --- | --- |
| 克隆仓库 & 切换到项目根目录 | （自行完成） |
| 安装依赖 | `uv sync` |
| 可选：安装真实 relayer 依赖 | `uv add py-clob-client py-builder-signing-sdk` |
| 自检 | `uv run pytest -q` |

---

## 2. 配置（必做）
1. 复制 `config/service.example.toml` → `config/service.toml`，只保留实际需要的市场（`[[market]]`）。
2. 在同目录创建 `config/secrets.local.toml`（已 gitignore），用来放置密钥与 builder 凭证。
3. 填写以下字段（示例见 `*.example` 文件）：
   - `[relayer]`：`type`, `base_url`, `dry_run`, `private_key`, `chain_id`, `timeout_s`
   - `[relayer.builder]`（推荐）：  
     - 本地模式：`mode = "local"` 并提供 `api_key / api_secret / api_passphrase`
     - 远程模式：`mode = "remote"` 并提供 `url / token`
4. 若你更习惯使用环境变量，也可以设置：
   ```
   setx POLY_BUILDER_API_KEY "<key>"
   setx POLY_BUILDER_SECRET "<secret>"
   setx POLY_BUILDER_PASSPHRASE "<passphrase>"
   setx POLY_BUILDER_REMOTE_URL "<url>"      # 可选
   setx POLY_BUILDER_TOKEN "<token>"         # 可选
   ```
   CLI 会优先读取环境变量；空缺的字段再由 `secrets.local.toml` 补齐。
5. **验证 builder 凭证**  
   ```
   uv run python -m polybot.cli builder-health --config config/service.toml --json
   ```
   正常输出 `builder ok...` 代表 py-clob-client + BuilderConfig 可以正确生成签名；若失败会给出缺失字段或凭证错误的提示。

---

## 3. 烟雾测试（dry-run）
1. **预检查配置**  
   ```
   uv run python -m polybot.cli preflight --config config/service.toml
   ```
2. **干跑下单（不会触发真实订单）**  
   ```
   uv run python -m polybot.cli smoke-live \
       --config config/service.toml \
       <market_id> <outcome_id> buy 0.40 1 \
       --base-url https://clob.polymarket.com \
       --private-key 0x... \
       --json
   ```
3. 确认命令输出 `placed=1 accepted=1`（或 JSON 中 `accepted:1`）。若 dry-run 都无法执行，请先排查网络或密钥配置。

---

## 4. 实盘最小流（Builder 模式）
> ⚠️ 操作前请确保 Builder 账户中已有 USDC。Polymarket Builder 使用你头像下方的 Profile Address（亦即 `funder`），需要把 USDC 充值到该地址后，Builder API 才能代表你下单。

1. **确保配置为实盘**：在 `config/secrets.local.toml` 中设置 `dry_run = false`。
2. **执行一次交易烟雾测试**（最常用命令）：
  ```
  uv run python -m polybot.cli relayer-live-order-config \
      --config config/service.toml \
      0x1fbeca90a39253081b032a9990da1cb5b25573d4e213327b5b0f0c222b05be6a \
      37902884120561856159354666911594986421517777792635262864250023116967352650864 \
      buy 0.39 5 \
      --confirm-live \
      --json
  ```
  - **参数顺序必须是**：`market_id outcome_id side price size`。若顺序错误，CLI 会提示 “invalid choice: ... (choose from buy, sell)”。
  - 如果只想提供网页 URL，可追加 `--url "https://polymarket.com/event/..."`
    - 示例：`... --confirm-live --url "https://polymarket.com/event/first-to-5k-gold-or-eth?tid=..." --json`
    - 自动解析 URL 并覆盖 `market_id/outcome_id`，避免再手动查 IDs。
   - `--confirm-live` 是安全保障，默认未加该参数会拒绝实盘下单。
3. **平仓示例**（sell 命令与上方相同，只需改 `side`）：
   ```
   uv run python -m polybot.cli relayer-live-order-config \
       --config config/service.toml \
       <market_id> <outcome_id> sell 0.37 5 \
       --confirm-live --json
   ```
4. **常见错误检查**：
   | 输出 | 说明 | 处理 |
   | --- | --- | --- |
   | `error=not enough balance / allowance` | Builder 账户余额不足或未完成内部 allowance | 在 Builder Settings 中充值 / 刷新余额 |
   | `PolyApiException[... Request exception]` | Cloudflare/SSL 短暂异常 | 直接重试命令；若持续失败请检查网络代理 |
   | `invalid choice: '<market_id>' (choose from buy, sell)` | 参数顺序错误 | 按上表顺序重新输入 |

---

## 5. 运行多市场服务（可选）
1. 保证 `config/service.toml` 中列出的 `[[market]]` 已配置完整。
2. 启动服务：
   ```
   uv run python -m polybot.cli run-service --config config/service.toml
   ```
3. 服务退出后会自动打印 `status-summary`，也可以手动运行：
   ```
   uv run python -m polybot.cli status --db-url sqlite:///./polybot.db --verbose
   ```

---

## 6. 排错与支持
- **Builder 授权/余额**：Polymarket Builder 后台不会复用 MetaMask 余额，务必在网页 Builder Settings 中转入 USDC（建议 ≥5）。
- **如何查看订单是否成交**：
  - CLI：`uv run python -m polybot.cli orders-tail --db-url sqlite:///./polybot.db --json`
  - Polymarket 网页：Builder 账户历史记录。
- **更多命令**：请参考 `docs/commands-reference.md`，其中包含 Gamma/WS 工具、tgbot、本地诊断等命令。

---

## 7. 文件清单（部署相关）
| 文件 | 作用 |
| --- | --- |
| `config/service.toml` | 主配置（可提交） |
| `config/secrets.local.toml` | 机密覆盖（永不提交） |
| `config/service.example.toml` | 模板，展示所有字段 |
| `config/secrets.local.toml.example` | 机密模板，可用于新环境 |

如需将更多命令、数据库策略等信息回顾，可阅读 `docs/commands-reference.md` 与 `docs/handoff.md`。本指南仅保留“开箱即用”的关键步骤。
