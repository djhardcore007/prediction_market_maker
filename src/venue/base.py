"""Venue abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..core.types import Order, Trade, OrderBookSnapshot, Market


class Venue(ABC):
    name: str

    def __init__(self, name: str, fee_bps: float = 0.0):
        self.name = name
        self.fee_bps = fee_bps

    @abstractmethod
    def list_markets(self) -> Iterable[Market]: ...

    @abstractmethod
    def get_order_book(self, market_id: str) -> OrderBookSnapshot: ...

    @abstractmethod
    def place_orders(self, orders: List[Order]) -> List[Trade]: ...

    def compute_fee(self, notional: float) -> float:
        return notional * (self.fee_bps / 10000.0)
