import asyncio

from polybot.service.runner import ServiceRunner, MarketSpec
from polybot.observability.metrics import get_counter_labelled


class BoomRunner:
    def __init__(self, *args, **kwargs):
        pass

    async def run(self, *args, **kwargs):  # noqa: D401
        # Immediately raise to simulate task failure
        raise RuntimeError("boom")


async def _run_once(monkeypatch):
    # Monkeypatch QuoterRunner in service.runner to our BoomRunner
    import polybot.service.runner as srv

    monkeypatch.setattr(srv, "QuoterRunner", BoomRunner)
    sr = ServiceRunner(db_url=":memory:")
    specs = [MarketSpec(market_id="mX", outcome_yes_id="yes", ws_url="ws://invalid", max_messages=1, subscribe=False)]
    await sr.run_markets(specs)


def test_service_runner_catches_task_errors(monkeypatch):
    base = get_counter_labelled("service_task_errors", {"market": "mX"})
    asyncio.run(_run_once(monkeypatch))
    now = get_counter_labelled("service_task_errors", {"market": "mX"})
    assert now == base + 1

