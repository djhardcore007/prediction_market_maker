"""Polymarket adapter.

Offline-friendly skeleton for interacting with Polymarket style AMM/orderbooks.
Real API integration often uses GraphQL endpoints and/or REST; we provide a
``dry_run`` mode that fabricates a simple one-level book so examples work
without network credentials.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, AsyncIterator, Dict
import os

from .base import Venue
from ..core.types import Market, OrderBookSnapshot, Order, Trade, BookLevel
from .ws_client import BaseWSClient

try:  # optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:  # optional websocket dependency
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # type: ignore


class PolymarketVenue(Venue):
    def __init__(
        self,
        name: str = "polymarket",
        base_url: str = "https://gamma-api.polymarket.com",
        markets_url: str = "https://clob.polymarket.com/markets",
        dry_run: bool = True,
        timeout: float = 5.0,
    ):
        super().__init__(name)
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        self.base_url = base_url.rstrip("/")
        self.markets_url = markets_url
        self.dry_run = dry_run
        self.timeout = timeout
        self._last_book: Dict[str, OrderBookSnapshot] = {}

    def list_markets(self) -> Iterable[Market]:
        """Return markets.

        In dry_run returns an empty list; real integration queries GraphQL or REST.
        """
        if self.dry_run or requests is None:
            return []
        try:  # pragma: no cover - avoid external calls in tests
            # Prefer CLOB markets endpoint which returns broader set
            resp = requests.get(self.markets_url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []
        markets: List[Market] = []
        # CLOB endpoint returns list of market dicts
        items = data if isinstance(data, list) else data.get("markets", [])
        for item in items:
            mkt_id = str(item.get("id") or item.get("market_id") or "")
            symbol = item.get("question") or item.get("name") or mkt_id
            if mkt_id:
                markets.append(Market(id=mkt_id, symbol=symbol, venue=self.name))
        return markets

    def get_order_book(self, market_id: str) -> OrderBookSnapshot:
        """Return fabricated or fetched one-level order book.

        Polymarket often exposes AMM reserves rather than traditional ladders;
        this simplifies to a mid ± tick synthetic book for tutorials.
        """
        # Serve cached snapshot if available (stabilizes tests/stream consumers)
        cached = self._last_book.get(market_id)
        if cached is not None:
            return cached
        if self.dry_run or requests is None:
            return OrderBookSnapshot(
                market_id=market_id,
                bids=[BookLevel(0.49, 80)],
                asks=[BookLevel(0.51, 80)],
            )
        try:  # pragma: no cover
            # Attempt generic orderbook path; Polymarket specifics may differ.
            resp = requests.get(
                f"{self.base_url}/v1/markets/{market_id}/orderbook",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            ob = resp.json()
        except Exception:
            return OrderBookSnapshot(
                market_id=market_id,
                bids=[BookLevel(0.49, 80)],
                asks=[BookLevel(0.51, 80)],
            )
        try:
            bids_raw = ob.get("bids") or []
            asks_raw = ob.get("asks") or []

            def to_level(x):
                if isinstance(x, (list, tuple)) and len(x) >= 2:
                    return BookLevel(float(x[0]), float(x[1]))
                if isinstance(x, dict):
                    return BookLevel(float(x.get("price", 0)), float(x.get("size", 0)))
                raise ValueError

            bids = [to_level(x) for x in bids_raw][:1]
            asks = [to_level(x) for x in asks_raw][:1]
            if not bids:
                bids = [BookLevel(0.49, 80)]
            if not asks:
                asks = [BookLevel(0.51, 80)]
        except Exception:
            bids = [BookLevel(0.49, 80)]
            asks = [BookLevel(0.51, 80)]
        snap = OrderBookSnapshot(market_id=market_id, bids=bids, asks=asks)
        self._last_book[market_id] = snap
        return snap

    def place_orders(self, orders: List[Order]) -> List[Trade]:
        if self.dry_run:
            return []
        raise NotImplementedError("Polymarket trading integration not implemented.")

    async def stream_order_books(
        self, market_id: str, interval_s: float = 1.0
    ) -> AsyncIterator[OrderBookSnapshot]:
        """Yield synthetic or real order book snapshots asynchronously.

        Dry-run mode emits a small random walk around mid 0.50. Real mode would
        connect to Polymarket’s WS/GraphQL subscriptions and parse updates.
        """
        import random, asyncio

        if self.dry_run or websockets is None:
            mid = 0.50
            while True:
                mid += random.uniform(-0.006, 0.006)
                mid = max(0.01, min(0.99, mid))
                yield OrderBookSnapshot(
                    market_id=market_id,
                    bids=[BookLevel(round(mid - 0.01, 4), 80)],
                    asks=[BookLevel(round(mid + 0.01, 4), 80)],
                )
                await asyncio.sleep(interval_s)
        else:  # pragma: no cover
            async with BaseWSClient(
                url="wss://example.polymarket.ws/stream",  # TODO: replace
                subscribe_template={"type": "subscribe"},
                unsubscribe_template={"type": "unsubscribe"},
                markets_array_field="markets",
            ) as client:
                await client.subscribe([market_id])
                async for msg in client.messages():
                    # Placeholder mapping logic
                    book = msg.get("book") or {}
                    bid = book.get("bid", 0.49)
                    ask = book.get("ask", 0.51)
                    yield OrderBookSnapshot(
                        market_id=market_id,
                        bids=[BookLevel(float(bid), 80)],
                        asks=[BookLevel(float(ask), 80)],
                    )
