"""Risk limits and checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Limits:
    max_notional: float
    per_market_max_position: float

    def within_notional(self, notional: float) -> bool:
        return notional <= self.max_notional

    def within_position(self, position: float) -> bool:
        return abs(position) <= self.per_market_max_position
