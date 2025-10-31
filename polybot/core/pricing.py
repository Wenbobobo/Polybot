from __future__ import annotations

from math import floor


def round_to_tick(price: float, tick: float) -> float:
    if tick <= 0:
        return price
    steps = floor(price / tick + 1e-9)
    return round(steps * tick, 10)


def is_valid_price(price: float) -> bool:
    return 0.0 <= price <= 1.0


def sum_prices(prices: list[float]) -> float:
    return round(sum(prices), 10)

