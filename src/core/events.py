"""Event structures used in the system (market data, orders, trades)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import Order, Trade, OrderBookSnapshot


@dataclass
class MarketDataEvent:
    book: OrderBookSnapshot
    ts: float  # seconds since epoch


@dataclass
class OrderEvent:
    order: Order
    ts: float


@dataclass
class TradeEvent:
    trade: Trade
    ts: float
    order_id: Optional[str] = None
