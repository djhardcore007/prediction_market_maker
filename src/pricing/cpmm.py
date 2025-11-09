"""CPMM (constant product) intuition helper for binary pools.

Not a full AMM book; just a helper to compute implied price from pool reserves.
"""

from __future__ import annotations

from typing import Tuple


def implied_price_binary(x_yes: float, x_no: float) -> float:
    """Implied probability for YES from constant-product reserves.

    p_yes = x_no / (x_yes + x_no)  if using x_yes * x_no = k, marginal price approx.
    """
    total = x_yes + x_no
    if total <= 0:
        return 0.5
    return x_no / total


def trade_outcome(x_yes: float, x_no: float, buy_yes: float) -> Tuple[float, float]:
    """Apply a naive trade and return new reserves (toy model)."""
    return max(0.0, x_yes + buy_yes), max(0.0, x_no - buy_yes)
