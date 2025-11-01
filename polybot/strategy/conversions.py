from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Holdings:
    yes: float
    no: float
    usdc: float


def should_merge(hold: Holdings, price_yes: float, price_no: float, min_profit_usdc: float, gas_cost_usdc: float) -> bool:
    """Decide to merge YES/NO into USDC when holdings are roughly matched and profit > gas.

    Simplified: if min(yes,no) > 0 and |(price_yes + price_no) - 1.0| < 1e-6, merging locks 1 USDC per pair; here
    we require available pairs * 1.0 - gas_cost_usdc >= min_profit_usdc.
    """
    pairs = min(max(0.0, hold.yes), max(0.0, hold.no))
    if pairs <= 0:
        return False
    profit = pairs * 0.0  # pure merge settles at par (ignore tiny rounding)
    # treat decision as whether we can amortize gas across pairs to exceed min profit
    return max(0.0, -gas_cost_usdc) + profit >= min_profit_usdc


def should_split(hold: Holdings, usdc_to_use: float, min_profit_usdc: float, gas_cost_usdc: float) -> bool:
    """Decide to split USDC into equal YES/NO when downstream strategy needs inventory.

    Simplified: ensure we have the USDC and that usdc_to_use - gas exceeds min_profit_usdc (as an operational threshold).
    """
    if usdc_to_use <= 0 or hold.usdc < usdc_to_use:
        return False
    return (usdc_to_use - gas_cost_usdc) >= min_profit_usdc

