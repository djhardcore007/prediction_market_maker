"""Polymarket adapter (skeleton).

This is a placeholder showing where REST/WebSocket integration would live.
"""

from __future__ import annotations

from typing import Iterable, List

from .base import Venue
from ..core.types import Market, OrderBookSnapshot, Order, Trade, BookLevel


class PolymarketVenue(Venue):
    def list_markets(self) -> Iterable[Market]:
        # TODO: Implement API calls to fetch markets
        return []

    def get_order_book(self, market_id: str) -> OrderBookSnapshot:
        # TODO: Implement order book retrieval via WS snapshot
        return OrderBookSnapshot(
            market_id=market_id,
            bids=[BookLevel(0.49, 100)],
            asks=[BookLevel(0.51, 100)],
        )

    def place_orders(self, orders: List[Order]) -> List[Trade]:
        # TODO: Submit via API and return confirmed trades/fills
        return []
