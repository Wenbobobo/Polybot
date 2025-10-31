import asyncio

import pytest

from polybot.ingestion.market_scheduler import run_market_refresh_loop


class FlakyGamma:
    def __init__(self):
        self.calls = 0

    def list_markets(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary error")
        return []


class Wrapper:
    def __init__(self, g):
        self.g = g

    def list_markets(self):
        return self.g.list_markets()


class GC:
    def __init__(self, wrapper):
        self.wrapper = wrapper

    def list_markets(self):
        return self.wrapper.list_markets()


def test_market_scheduler_handles_errors_and_jitter(event_loop):
    import sqlite3
    from polybot.storage import schema
    con = sqlite3.connect(":memory:")
    schema.create_all(con)
    g = FlakyGamma()
    gamma = GC(Wrapper(g))

    async def run():
        await run_market_refresh_loop(con, gamma, interval_ms=10, iterations=2, jitter_ratio=0.0, backoff_ms=1)

    event_loop.run_until_complete(run())
    assert g.calls >= 2

