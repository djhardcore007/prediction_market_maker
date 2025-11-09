"""Lightweight order book / pool state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..core.types import BookLevel, OrderBookSnapshot


@dataclass
class RollingBook:
    market_id: str
    window: int = 100
    history: List[OrderBookSnapshot] = field(default_factory=list)

    def push(self, snap: OrderBookSnapshot):
        self.history.append(snap)
        if len(self.history) > self.window:
            self.history.pop(0)

    def last(self) -> OrderBookSnapshot | None:
        return self.history[-1] if self.history else None

    def last_mid(self) -> float | None:
        last = self.last()
        return last.mid() if last else None
