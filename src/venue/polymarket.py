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
        dry_run: bool = True,
        timeout: float = 5.0,
        api_key: Optional[str] = None,
    ):
        super().__init__(name)
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.timeout = timeout
        self._last_book: Dict[str, OrderBookSnapshot] = {}
        # Optional API key support for authenticated/ratelimited endpoints
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        # Optional WS user-channel auth triplet (for private/user subscriptions)
        self.api_secret = os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")

    def _headers(self) -> Dict[str, str]:
        """Build HTTP headers, including optional Polymarket API key.

        Polymarket public endpoints often work without a key, but providing an
        API key may improve rate limits or be required in some environments.
        """
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            # Common header name used by Polymarket CLOB
            headers["X-API-KEY"] = self.api_key
        return headers

    def _ws_auth(self) -> Optional[Dict[str, str]]:
        """Return WS auth payload for Polymarket user channel if fully configured.

        Expects three envs (or ctor-provided values) set:
        - POLYMARKET_API_KEY
        - POLYMARKET_API_SECRET
        - POLYMARKET_API_PASSPHRASE

        The expected format is {"apiKey": key, "secret": secret, "passphrase": passphrase}.
        """
        if self.api_key and self.api_secret and self.api_passphrase:
            return {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "passphrase": self.api_passphrase,
            }
        return None

    def list_markets(self) -> Iterable[Market]:
        """Return markets using Gamma API (best-effort mapping).

        In dry_run returns an empty list; otherwise calls GET {base_url}/markets.
        """
        if self.dry_run or requests is None:
            return []
        try:  # pragma: no cover - avoid external calls in tests
            url = f"{self.base_url}/markets"
            resp = requests.get(url, timeout=self.timeout, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []
        markets: List[Market] = []
        # Endpoint may return a list or an object with a 'markets' key
        items = (
            data
            if isinstance(data, list)
            else (data.get("markets", []) if isinstance(data, dict) else [])
        )
        for item in items:
            # Prefer canonical id + question title when available
            if not isinstance(item, dict):
                continue
            mkt_id = str(item.get("id") or item.get("market_id") or "")
            symbol = (
                item.get("question")
                or item.get("name")
                or item.get("market_slug")
                or mkt_id
            )
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
                headers=self._headers(),
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

        - Synthetic mode: small random walk around 0.50.
        - Live mode: connects to Polymarket CLOB WS at
          wss://ws-subscriptions-clob.polymarket.com/ws/market and subscribes
          to the MARKET channel using asset IDs.

        Note: The Polymarket WS market channel expects asset IDs
        (token IDs). If ``market_id`` isn't a numeric asset ID, this
        falls back to synthetic snapshots.
        """
        import random, asyncio, json as _json

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
            return

        # Treat market_id as an asset_id if it's all digits (Polymarket token id format)
        asset_id = market_id if market_id.isdigit() else None
        if not asset_id:
            # Can't subscribe without a token/asset id; provide synthetic
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
            return

        ws_base = os.getenv(
            "POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com"
        )
        ws_url = ws_base.rstrip("/") + "/ws/market"
        sub_msg = {"assets_ids": [asset_id], "type": "market", "auth": self._ws_auth()}

        async def _ping(ws):
            try:
                while True:
                    await ws.send("PING")
                    await asyncio.sleep(10)
            except Exception:
                return

        try:  # pragma: no cover
            async with websockets.connect(ws_url) as ws:
                await ws.send(_json.dumps(sub_msg))

                # start ping task
                ping_task = asyncio.create_task(_ping(ws))
                try:
                    async for raw in ws:
                        # Skip heartbeat strings
                        if raw in ("PING", "PONG"):
                            continue
                        try:
                            data = _json.loads(raw)
                        except Exception:
                            continue
                        # Server may send lists; normalize to iterable of dicts
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            event_type = item.get("event_type")
                            if event_type != "book":
                                continue
                            bids_raw = item.get("bids", [])
                            asks_raw = item.get("asks", [])

                            def _to_level(x):
                                # Expect dicts with 'price' and 'size' strings
                                if isinstance(x, dict):
                                    return BookLevel(
                                        float(x.get("price", 0.0)),
                                        float(x.get("size", 0.0)),
                                    )
                                if isinstance(x, (list, tuple)) and len(x) >= 2:
                                    return BookLevel(float(x[0]), float(x[1]))
                                return None

                            bids = [
                                lvl for lvl in (_to_level(x) for x in bids_raw) if lvl
                            ][:1]
                            asks = [
                                lvl for lvl in (_to_level(x) for x in asks_raw) if lvl
                            ][:1]
                            if not bids or not asks:
                                continue
                            yield OrderBookSnapshot(
                                market_id=market_id, bids=bids, asks=asks
                            )
                finally:
                    ping_task.cancel()
        except Exception:
            # Fallback to synthetic if WS connection fails
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
