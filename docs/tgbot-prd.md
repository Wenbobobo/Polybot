# Telegram Bot PRD (C-End Companion)

## Objective
Design a Telegram companion bot that lets whitelisted operators request Polymarket market context, place/close trades (after explicit confirmation), and review health checks without touching the CLI. The bot is a thin UX layer over the existing service runner + CLI stack and must respect all builder readiness gates.

## Target Users
- **Primary operator:** power user already familiar with Polymarket markets and the CLI but wants lightweight mobile controls.
- **Observer/reviewer:** read-only teammate who monitors health/positions and escalates back to the operator if anomalies appear.

## Guiding Principles
1. **Safety first:** every live action reuses the CLI flow (`builder-health`, `relayer-approve-*`, `market-trade`) and requires explicit confirmation; default to dry-run previews.
2. **Deterministic auditing:** commands emit the same JSON blobs the CLI produces so logs can be replayed; no hidden heuristics.
3. **Config-only:** the bot reads TOML configs (`config/service.toml`, `config/tgbot.toml`) plus `secrets.local.toml`; no runtime environment variables.
4. **Windows + uv friendly:** local development/testing must run through `uv run python -m polybot.tgbot ...`.

## MVP Feature Set
| Feature | Description | Dependencies |
| --- | --- | --- |
| `/start` | Authenticate the chat, explain allowed commands, show current config profile. | `tgbot` config (`allowed_user_ids`, `default_config_path`). |
| `/status [--json]` | Return summary from `status` or `status-top`; include builder allowance gauges so operators see readiness. | CLI status command, builder metrics instrumentation. |
| `/market <query|url>` | Resolve market via `market-trade` helper, return title/rule_hash/prices/spread snapshot. | `market-trade` resolver path + CLOB price helpers. |
| `/trade <url-or-id> <side> <price> <size>` | Dry-run a `market-trade` call (no `--confirm-live`) and show the plan plus builder/allowance preflight. | CLI orchestration; needs builder-health + smoke-live outputs. |
| `/confirm <token>` | Executes the buffered trade with `--confirm-live` after the operator types the confirmation token sent in `/trade`. | Persistent chat state; expiring tokens. |
| `/close <market>` | Shortcut to run `market-trade --close-only`; supports “flatten position” flows when already long/short. | Same CLI entrypoint. |
| `/allowance` | Show builder USDC/outcome allowances (calls `relayer-approve-* --get-only`). | CLI allowance commands. |

## Extended Backlog (post-MVP)
1. Multimarket watchlists and push alerts for rule_hash changes or builder failures.
2. Streaming fills/orders to a private channel for audit.
3. Multisig approval mode (two operators must confirm before a trade executes).

## Interaction Flow (Happy Path)
1. `/market https://polymarket.com/event/...`: bot resolves slug → market/outcome IDs, fetches latest `price/midpoint/spread`, and returns a card with share availability + tick size.
2. `/trade <url> buy 0.41 10`: bot runs `market-trade` without `--confirm-live`, displays:
   - Builder-health snapshot
   - Allowance before/after (dry-run)
   - Planned entry order JSON
   - Optional auto-close plan
   Bot sends `Confirm with /confirm <token> (valid 60s)`.
3. `/confirm 9fd2a1`: bot replays the same call with `--confirm-live`, streaming ack + fill events back to the chat and concluding with `position_delta`.
4. `/close <url>` later uses `market-trade`’s `--close` flag to fully exit.

## Error Handling & Safety
- All commands require the chat id/user id to be in `allowed_users`. Unauthorized requests receive “not whitelisted” and are logged.
- `/trade` fails fast if builder-health or allowances are invalid; the bot surfaces the exact CLI stderr so operators know whether to fund the wallet or refresh allowances.
- Confirmation tokens expire (60s configurable) and are single-use to avoid replay.
- Rate limit per user (e.g., max 5 live trades/10 min) to prevent runaway loops if Telegram keyboard is spammed.

## Configuration
Create `config/tgbot.example.toml`:
```toml
[tgbot]
bot_token = "123456:ABC"
config_path = "config/service.toml"
status_command = "status-top"
allowed_users = [123456789]
confirm_ttl_s = 60
```
Secrets overlay lives beside service config (same pattern as relayer secrets).

## Telemetry & Logging
- Structured JSON logs per request: `{"cmd":"trade","chat_id":...,"config":"config/service.toml","builder_balance":"123.4","result":"confirmed"}`.
- Prometheus counters for `/trade` attempts, confirmations, failures, and command latency histograms.

## Testing Strategy
1. Unit tests for command parsing, confirmation token lifecycle, and permission checks (pure functions).
2. Integration tests hitting a fake Telegram transport + stubbed CLI process (use recorded CLI outputs).
3. Replay tests that feed recorded `/trade` transcripts to guarantee deterministic behavior.

## Dependencies & Risks
- Requires Telegram Bot API network access; plan for toggleable offline mode (commands queue and run locally in CI).
- Must sandbox builder secrets: CLI subprocess inherits only the config + secrets we point to; never echo API keys back to Telegram.
- Align release timing with completion of builder readiness metrics so `/status` shows allowances.

## Success Metrics
- 100% of manual “single market trade” flows can be executed from Telegram without touching PowerShell.
- Time-to-trade reduced (<30s from `/market` to `/confirm` for practiced user).
- No unauthorized command executions; confirmations logged with matching CLI order IDs.

## Open Questions
1. Should the bot handle multi-leg strategies (Dutch/Spread) or remain single-market?
2. Where to store chat state (on-disk JSON vs. SQLite table vs. reuse `polybot.db`)?
3. Do we enforce positional limits per chat inside the bot or rely on the execution engine?

These will be resolved once the core trading loop proves stable and builder observability metrics land.
