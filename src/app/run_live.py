"""Entry point for live trading (mock for now)."""

from __future__ import annotations

import time

from .main import build_mock_environment
from ..exec.router import route


def main():  # pragma: no cover - manual run
    store, venue, strat = build_mock_environment()
    for _ in range(3):
        for market in venue.list_markets():
            book = venue.get_order_book(market.id)
            orders = strat.quote(book)
            trades = route(venue, orders)
            # update inventory from trades
            for t in trades:
                store.inventory.update(t)
        time.sleep(0.5)
    print("Finished live mock loop")


if __name__ == "__main__":  # pragma: no cover
    main()
