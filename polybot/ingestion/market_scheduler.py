from __future__ import annotations

import asyncio
import time
from typing import Optional

from .markets import refresh_markets, GammaClientProto


async def run_market_refresh_loop(con, gamma_client: GammaClientProto, interval_ms: int = 60000, iterations: Optional[int] = None):
    count = 0
    while True:
        refresh_markets(con, gamma_client)
        count += 1
        if iterations is not None and count >= iterations:
            break
        await asyncio.sleep(interval_ms / 1000.0)

