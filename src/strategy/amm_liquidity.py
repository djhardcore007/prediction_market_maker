"""AMM liquidity provisioning strategy placeholder."""

from __future__ import annotations

from typing import List

from .base import Strategy
from ..core.types import OrderBookSnapshot, Order


class AMMLiquidityStrategy(Strategy):
    def quote(self, book: OrderBookSnapshot) -> List[Order]:
        # For AMMs you adjust pool parameters; here we do nothing.
        return []
