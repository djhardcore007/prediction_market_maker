"""App bootstrap for live or backtest modes."""

from __future__ import annotations

from ..venue.mock import MockVenue
from ..core.types import Market
from ..state.store import Store
from ..strategy.binary_mm import BinaryMMStrategy
from ..exec.router import route


def build_mock_environment() -> tuple[Store, MockVenue, BinaryMMStrategy]:
    store = Store()
    venue = MockVenue()
    m = Market(id="YES_2025_EVENT", symbol="EVT-YES", venue=venue.name)
    venue.add_market(m)
    store.upsert_market(m)
    strat = BinaryMMStrategy()
    return store, venue, strat
