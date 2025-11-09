"""Small utilities."""

from __future__ import annotations

import math
from typing import Optional


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def to_prob(price: float, tick: float = 0.01) -> float:
    """Map price in [0,1] to a clamped probability, respecting tick size."""
    p = clamp(price, 0.0, 1.0)
    # round to nearest tick (banker's rounding). For quote-side aware rounding
    # use floor_to_tick/ceil_to_tick.
    if tick > 0:
        p = round(p / tick) * tick
    return clamp(p, 0.0, 1.0)


def floor_to_tick(price: float, tick: float = 0.01) -> float:
    """Floor to tick, clamped to [0,1]."""
    if tick <= 0:
        return clamp(price, 0.0, 1.0)
    return clamp(math.floor(price / tick + 1e-12) * tick, 0.0, 1.0)


def ceil_to_tick(price: float, tick: float = 0.01) -> float:
    """Ceil to tick, clamped to [0,1]."""
    if tick <= 0:
        return clamp(price, 0.0, 1.0)
    return clamp(math.ceil(price / tick - 1e-12) * tick, 0.0, 1.0)


def safe_div(n: float, d: float, default: Optional[float] = None) -> Optional[float]:
    if d == 0:
        return default
    return n / d
