"""Inventory + microstructure aware binary market making strategy (simplified)."""

from __future__ import annotations

import uuid
from typing import List

from .base import Strategy
from ..core.types import Order, OrderSide, OrderBookSnapshot
from ..pricing.lmsr import LMSR
from ..core.utils import floor_to_tick, ceil_to_tick
from ..pricing.inventory import skew_probabilities


class BinaryMMStrategy(Strategy):
    def __init__(
        self,
        spread_bps: float = 100.0,
        inventory_alpha: float = 0.002,
        lmsr_b: float = 100.0,
    ):
        self.spread_bps = spread_bps
        self.inventory_alpha = inventory_alpha
        self.model = LMSR(b=lmsr_b)
        self.inventory_yes = 0.0  # track net YES exposure

    def update_inventory(self, delta_yes: float):
        self.inventory_yes += delta_yes

    def quote(self, book: OrderBookSnapshot) -> List[Order]:
        mid = book.mid() or 0.5
        base_probs = [mid, 1 - mid]
        adj_probs = skew_probabilities(
            base_probs, self.inventory_yes, self.inventory_alpha
        )
        # convert probability to price; apply symmetric spread
        p_yes = adj_probs[0]
        # spread_bps denotes total spread in bps; half-spread is half of that
        half_spread = self.spread_bps / 20000.0
        raw_bid = max(0.0, p_yes - half_spread)
        raw_ask = min(1.0, p_yes + half_spread)
        bid = floor_to_tick(raw_bid)
        ask = ceil_to_tick(raw_ask)
        # ensure spread doesn't collapse; if equal, widen minimally
        if bid >= ask:
            if bid >= 1.0:
                bid = max(0.0, bid - 0.01)
            else:
                ask = min(1.0, ask + 0.01)
        qty = 10.0  # stub size
        return [
            Order(str(uuid.uuid4()), book.market_id, "YES", OrderSide.BUY, qty, bid),
            Order(str(uuid.uuid4()), book.market_id, "YES", OrderSide.SELL, qty, ask),
        ]
