"""Simple order router."""

from __future__ import annotations

from typing import List

from ..core.types import Order, Trade
from ..venue.base import Venue


def route(venue: Venue, orders: List[Order]) -> List[Trade]:
    return venue.place_orders(orders)
