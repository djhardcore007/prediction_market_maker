"""Backtesting engine."""

from __future__ import annotations

from typing import Iterable, Callable

from ..venue.mock import MockVenue
from ..state.store import Store
from ..strategy.base import Strategy

Scenario = Iterable[tuple[str, float]]  # (market_id, new_mid)


def run_scenario(
    store: Store, venue: MockVenue, strategy: Strategy, scenario: Scenario
):
    for market_id, new_mid in scenario:
        venue.move_price(market_id, new_mid)
        book = venue.get_order_book(market_id)
        orders = strategy.quote(book)
        trades = venue.place_orders(orders)
        for t in trades:
            store.inventory.update(t)
