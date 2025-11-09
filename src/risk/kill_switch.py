"""Kill switch logic."""

from __future__ import annotations


class KillSwitch:
    def __init__(self, max_loss: float):
        self.max_loss = max_loss
        self.triggered = False

    def check(self, unrealized_pnl: float):
        if unrealized_pnl <= -abs(self.max_loss):
            self.triggered = True
        return self.triggered
