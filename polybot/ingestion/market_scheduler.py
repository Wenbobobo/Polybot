from __future__ import annotations

import asyncio
import random
from typing import Optional

from .markets import refresh_markets, GammaClientProto


async def run_market_refresh_loop(
    con,
    gamma_client: GammaClientProto,
    interval_ms: int = 60000,
    iterations: Optional[int] = None,
    jitter_ratio: float = 0.1,
    backoff_ms: int = 200,
):
    """Periodic markets refresh with jitter and simple backoff on errors.

    - Adds +/- jitter_ratio to the interval to avoid thundering herds.
    - On exception, waits backoff_ms before next attempt and continues.
    """
    count = 0
    while True:
        try:
            refresh_markets(con, gamma_client)
        except Exception:
            await asyncio.sleep(max(0, backoff_ms) / 1000.0)
        count += 1
        if iterations is not None and count >= iterations:
            break
        jitter = 1.0 + random.uniform(-jitter_ratio, jitter_ratio)
        wait_ms = max(0, int(interval_ms * jitter))
        await asyncio.sleep(wait_ms / 1000.0)
