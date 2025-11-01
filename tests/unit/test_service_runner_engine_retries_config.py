from polybot.service.runner import ServiceRunner


def test_service_runner_passes_engine_retry_config(monkeypatch):
    captured = {}

    class CapturingEngine:
        def __init__(self, relayer, audit_db=None, max_retries=0, retry_sleep_ms=0, sleeper=None):
            captured["max_retries"] = max_retries
            captured["retry_sleep_ms"] = retry_sleep_ms

        def execute_plan(self, plan):
            return None

    import polybot.service.runner as srv

    monkeypatch.setattr(srv, "ExecutionEngine", CapturingEngine)
    sr = ServiceRunner(db_url=":memory:", engine_max_retries=3, engine_retry_sleep_ms=50)
    # No markets needed; just invoke run to instantiate engine
    import asyncio

    asyncio.run(sr.run_markets([]))
    assert captured.get("max_retries") == 3
    assert captured.get("retry_sleep_ms") == 50

