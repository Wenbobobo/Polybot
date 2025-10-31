Agent working notes and conventions for this repo

Scope
- This file applies to the entire repository.

Principles
- TDD first: write tests before adding implementation. Keep unit tests fast and deterministic.
- Prefer pure functions and explicit dependencies for testability.
- Small, composable modules; avoid hidden globals.
- All configuration is file-based (TOML). No environment variables for required config.
- Windows + PowerShell + uv are first-class for local dev.

Style
- Python 3.12. Use type hints and dataclasses where practical.
- Avoid over-abstraction; solve the problem at hand with minimal complexity.
- Log in structured JSON; do not log secrets or private keys.

Architecture (Polymarket-only, Phase 1)
- adapters/polymarket: Gamma (REST), Orderbook (WS), Relayer (orders), CTF (merge/split) interfaces.
- core: domain models, math utilities, risk checks.
- exec: strategy engine and execution policies.
- storage: schema and DB access (SQLite dev, PostgreSQL production).
- observability: logging, metrics, recordings.

Testing
- Unit tests under tests/unit mirror module names.
- Integration tests under tests/integration provide fake services and record/replay harness.
- Keep high coverage (90%+ overall; 95%+ for strategy/execution paths).

Docs
- Keep docs/technical-plan.md, docs/roadmap.md, docs/prd.md, docs/progress.md up to date.

