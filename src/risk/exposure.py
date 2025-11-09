"""Exposure and pseudo-greeks for prediction markets."""

from __future__ import annotations

from typing import Sequence


def delta_binary(p_yes: float, position_yes: float) -> float:
    """Pseudo-delta: sensitivity of book value to small probability shift.

    For binary, mark-to-market value ~ position_yes * p_yes.
    d(value)/d(p) = position_yes.
    """
    return position_yes


def portfolio_value_binary(p_yes: float, position_yes: float) -> float:
    return position_yes * p_yes


def entropy(probs: Sequence[float]) -> float:
    import math

    eps = 1e-12
    return -sum(p * math.log(max(p, eps)) for p in probs if p > 0)
