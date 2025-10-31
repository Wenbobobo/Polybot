Polybot (Phase 1 MVP)
=====================

Polymarket-focused arbitrage bot scaffolding with high-performance ingestion, forward-looking storage, strategy engines (Dutch Book + Spread Capture), and robust test suite. Built for Windows + PowerShell + uv.

Quick Start
- `uv sync`
- `uv run pytest -q` (all green)

Core Commands
- Status: `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db` (add `--verbose` for quotes + timings)
- Mock WS: `uv run python -m polybot.cli mock-ws --port 9000`
- Ingest WS: `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
- Quoter WS (simulate): `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9000 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- Record WS: `uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 recordings/out.jsonl --max-messages 3 --subscribe`
- Quoter Replay: `uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
- Refresh Markets (Gamma): `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
- Run Service: `uv run python -m polybot.cli run-service --config config/markets.example.toml`
- Metrics: `uv run python -m polybot.cli metrics`
- Prometheus Export: `uv run python -m polybot.cli metrics-export`
- Health: `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`

Docs
- PRD: `docs/prd.md`
- Technical Plan: `docs/technical-plan.md`
- Roadmap: `docs/roadmap.md`
- Deployment: `docs/deployment.md`
- Runbook: `docs/runbook.md`
- Acceptance: `docs/acceptance-checklist.md`, `docs/acceptance-walkthrough.md`

Notes
- Trading uses a FakeRelayer for safety in this phase. Wiring the real Polymarket relayer and CTF will follow.
