# MVP Acceptance Walkthrough (Phase 1)

This guide walks through verifying each item in `docs/acceptance-checklist.md` using built-in tools and commands on Windows + PowerShell + uv.

## 0) Setup
- Install deps: `uv sync`
- Run tests: `uv run pytest -q` (should be green)

## 1) Data & Ingestion
- Gamma normalization and DB upsert:
  - `uv run python -m polybot.cli refresh-markets https://gamma-api.polymarket.com --db-url sqlite:///./polybot.db`
  - Verify rows: `status` should show markets after you start ingestion (optional at this step).
- WS client + subscribe + translation:
  - Start a mock WS: `uv run python -m polybot.cli mock-ws --port 9000`
  - Ingest: `uv run python -m polybot.cli ingest-ws ws://127.0.0.1:9000 mkt-1 --db-url sqlite:///./polybot.db --max-messages 3`
  - Status: `uv run python -m polybot.cli status --db-url sqlite:///./polybot.db --verbose`
  - Verify applied/invalid counters; last_update_ts_ms updated; snapshots/deltas > 0.
- Scheduler (optional live check):
  - See tests for `run_ingestion_session` + `market_scheduler` for periodic snapshots and pruning.

## 2) Strategy & Execution
- Dutch Book detector and planner: covered by tests; see `tests/unit/test_dutch_book.py` and `tests/integration/test_dutch_book_execution.py`.
- Spread Capture planner and quoter:
  - Replay demo: `uv run python -m polybot.cli quoter-run-replay recordings/sample.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`
  - Verify orders in DB: `SELECT COUNT(*) FROM orders;` > 0
  - WS demo with mock:
    - `uv run python -m polybot.cli mock-ws --port 9001`
    - `uv run python -m polybot.cli quoter-run-ws ws://127.0.0.1:9001 mkt-1 yes --db-url sqlite:///./polybot.db --max-messages 3 --subscribe`
- Execution & persistence:
  - Exec audit: `SELECT * FROM exec_audit ORDER BY id DESC LIMIT 1;` contains plan_id, duration_ms, intents/acks JSON.
  - Orders and fills tables populated; cancels appear when quotes are replaced.

## 3) Observability & Ops
- JSON logs are printed to stdout by default.
- Metrics:
  - `uv run python -m polybot.cli metrics` prints counters including per-market labelled values.
  - `status --verbose` shows per-market quotes and engine timings (avg ms and count).
- Health:
  - `uv run python -m polybot.cli health --db-url sqlite:///./polybot.db --staleness-ms 30000`
  - Adjust staleness threshold to simulate stale status.

## 4) Service Orchestration (Simulation)
- Create a TOML config (or use `config/markets.example.toml` as a template).
- Start a mock WS server: `uv run python -m polybot.cli mock-ws --port 9002`
- Run service: `uv run python -m polybot.cli run-service --config config/markets.example.toml`
- Verify orders and audits are written; `status --verbose` shows activity.

## 5) Recording & Replay
- Record: `uv run python -m polybot.cli record-ws ws://127.0.0.1:9000 out.jsonl --max-messages 3 --subscribe`
- Replay: `uv run python -m polybot.cli quoter-run-replay out.jsonl mkt-1 yes --db-url sqlite:///./polybot.db`

## 6) Notes & Next Steps
- This MVP is offline/simulated for execution (FakeRelayer). Wiring real relayer (py-clob-client), CTF, and real Polymarket WS payloads are next.
- All required acceptance checks are covered by tests and the above commands.

