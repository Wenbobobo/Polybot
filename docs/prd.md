# PRD: Polymarket Arbitrage Bot (Phase 1)

Objective
- Build a reliable, automated arbitrage engine focused on Polymarket.

Users
- Internal operators (small private circle) in early stages.

Key Features
- High-performance data ingestion (WS-first, REST snapshots)
- Forward-looking storage (event-sourced, replayable)
- Strategy A: Dutch Book; Strategy B: Spread Capture
- Robust execution with health/risk controls
- Config via TOML; Windows + PowerShell + uv workflow

Non-Goals (Phase 1)
- Cross-platform, news/sweeping, Telegram bot (deferred until foundations complete)

Success Metrics (initial)
- Data latency/throughput SLOs met; deterministic replay
- Safe execution (no unintended net exposure); >=0 profit in pure-arb scenarios

