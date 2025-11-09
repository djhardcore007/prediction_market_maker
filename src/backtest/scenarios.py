"""Scenario generators."""

from __future__ import annotations

import random
from typing import Iterable


def random_walk(
    steps: int, start: float = 0.5, sigma: float = 0.02, seed: int | None = None
) -> Iterable[tuple[str, float]]:
    rng = random.Random(seed)
    mid = start
    market_id = "YES_2025_EVENT"
    for _ in range(steps):
        mid += rng.gauss(0, sigma)
        mid = max(0.01, min(0.99, mid))
        yield market_id, mid
