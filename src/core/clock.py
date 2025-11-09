"""Clock utilities to coordinate backtests and live loops."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class MarketClock:
    speed: float = 1.0  # 1.0 = real-time; >1 faster in backtests

    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float):
        time.sleep(max(0.0, seconds) / max(1e-9, self.speed))
