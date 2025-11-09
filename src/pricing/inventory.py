"""Inventory-aware pricing helpers."""

from __future__ import annotations

from typing import Sequence, List


def skew_probabilities(
    base_probs: Sequence[float], inventory: float, alpha: float = 0.001
) -> List[float]:
    """Apply a simple linear skew to binary probabilities based on inventory.

    Positive inventory (long YES) should reduce YES probability to encourage selling.
    We'll shift YES by -alpha * inventory, and re-normalize.
    """
    if len(base_probs) != 2:
        return list(base_probs)
    p_yes = base_probs[0]
    p_no = base_probs[1]
    p_yes_adj = p_yes - alpha * inventory
    p_no_adj = p_no + alpha * inventory
    s = p_yes_adj + p_no_adj
    if s <= 0:
        return [0.5, 0.5]
    return [max(0.0, min(1.0, p_yes_adj / s)), max(0.0, min(1.0, p_no_adj / s))]
