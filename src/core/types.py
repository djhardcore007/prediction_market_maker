"""Core type definitions for the market maker.

The focus is on binary prediction markets (YES/NO) but we keep it generic for N outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


@dataclass
class Market:
    id: str
    symbol: str
    outcomes: List[str] = field(default_factory=lambda: ["YES", "NO"])  # for binary
    tick_size: float = 0.01
    lot_size: int = 1
    venue: Optional[str] = None


@dataclass
class Position:
    market_id: str
    outcome: str  # e.g. YES
    size: float = 0.0  # positive long YES exposure; negative implies long NO for binary

    @property
    def signed_size(self) -> float:
        return self.size


@dataclass
class Order:
    id: str
    market_id: str
    outcome: str
    side: OrderSide
    qty: float
    price: float
    type: OrderType = OrderType.LIMIT


@dataclass
class Trade:
    order_id: str
    market_id: str
    outcome: str
    side: OrderSide
    qty: float
    price: float
    fee: float = 0.0


@dataclass
class BookLevel:
    price: float
    qty: float


@dataclass
class OrderBookSnapshot:
    market_id: str
    bids: List[BookLevel]
    asks: List[BookLevel]

    def mid(self) -> Optional[float]:
        if not self.bids or not self.asks:
            return None
        return (self.bids[0].price + self.asks[0].price) / 2

    def spread(self) -> Optional[float]:
        if not self.bids or not self.asks:
            return None
        return self.asks[0].price - self.bids[0].price


@dataclass
class Inventory:
    positions: Dict[str, Position] = field(default_factory=dict)

    def update(self, trade: Trade):
        key = f"{trade.market_id}:{trade.outcome}"
        pos = self.positions.get(key)
        signed_qty = trade.qty if trade.side == OrderSide.BUY else -trade.qty
        if pos is None:
            self.positions[key] = Position(
                market_id=trade.market_id, outcome=trade.outcome, size=signed_qty
            )
        else:
            pos.size += signed_qty

    def net_yes(self, market_id: str) -> float:
        yes_key = f"{market_id}:YES"
        return self.positions.get(yes_key, Position(market_id, "YES", 0)).size


@dataclass
class RiskLimits:
    max_notional: float
    per_market_max_position: float
    per_venue_max_orders_per_min: int
