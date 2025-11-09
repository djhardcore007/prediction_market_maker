"""Mock venue for backtesting/simulation.

Implements a simple one-level order book that moves according to scenario price.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from .base import Venue
from ..core.types import Market, OrderBookSnapshot, Order, Trade, BookLevel, OrderSide


class MockVenue(Venue):
    def __init__(self, name: str = "mock", fee_bps: float = 0.0):
        super().__init__(name, fee_bps)
        self._markets: Dict[str, Market] = {}
        self._mid: Dict[str, float] = {}
        self._depth: float = 100.0

    def add_market(self, market: Market, initial_mid: float = 0.5):
        self._markets[market.id] = market
        self._mid[market.id] = initial_mid

    def move_price(self, market_id: str, new_mid: float):
        self._mid[market_id] = max(0.0, min(1.0, new_mid))

    def list_markets(self) -> Iterable[Market]:
        return list(self._markets.values())

    def get_order_book(self, market_id: str) -> OrderBookSnapshot:
        mid = self._mid.get(market_id, 0.5)
        return OrderBookSnapshot(
            market_id=market_id,
            bids=[BookLevel(price=max(0.0, mid - 0.01), qty=self._depth)],
            asks=[BookLevel(price=min(1.0, mid + 0.01), qty=self._depth)],
        )

    def place_orders(self, orders: List[Order]) -> List[Trade]:
        # Immediate-or-cancel against the single-level book for simplicity
        trades: List[Trade] = []
        for o in orders:
            if o.qty <= 0:
                continue
            book = self.get_order_book(o.market_id)
            if o.side == OrderSide.BUY:
                best_ask = book.asks[0]
                if o.price >= best_ask.price:
                    qty = min(o.qty, best_ask.qty)
                    fee = self.compute_fee(qty * best_ask.price)
                    trades.append(
                        Trade(
                            o.id,
                            o.market_id,
                            o.outcome,
                            o.side,
                            qty,
                            best_ask.price,
                            fee,
                        )
                    )
            else:
                best_bid = book.bids[0]
                if o.price <= best_bid.price:
                    qty = min(o.qty, best_bid.qty)
                    fee = self.compute_fee(qty * best_bid.price)
                    trades.append(
                        Trade(
                            o.id,
                            o.market_id,
                            o.outcome,
                            o.side,
                            qty,
                            best_bid.price,
                            fee,
                        )
                    )
        return trades
