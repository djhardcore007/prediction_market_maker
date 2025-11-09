"""Kalshi adapter (skeleton)."""

from __future__ import annotations

from typing import Iterable, List

from .base import Venue
from ..core.types import Market, OrderBookSnapshot, Order, Trade, BookLevel


class KalshiVenue(Venue):
    def list_markets(self) -> Iterable[Market]:
        # TODO: API integration
        return []

    def get_order_book(self, market_id: str) -> OrderBookSnapshot:
        # TODO: WS or REST
        return OrderBookSnapshot(
            market_id=market_id, bids=[BookLevel(0.48, 50)], asks=[BookLevel(0.52, 50)]
        )

    def place_orders(self, orders: List[Order]) -> List[Trade]:
        return []
