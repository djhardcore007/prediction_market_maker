"""Kalshi adapter.

Borrows signing + environment approach from ``examples/kalshi/clients.py``:
message = TIMESTAMP(ms) + METHOD + FULL_PATH (including ``/trade-api/v2`` prefix).

Features:
* Demo vs Prod selection via ``KALSHI_ENV=demo|prod`` (defaults to provided base_url)
* Automatic RSA-PSS signing if ``KALSHI_API_KEY_ID`` and private key env available
* Dry-run mode fabricates minimal deterministic snapshots for offline tests

NOTE: Live calls require proper API key tier. Portfolio/order endpoints may 401
unless your account has sufficient access.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, AsyncIterator, Dict, Any
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta
from dotenv import load_dotenv  # type: ignore

from .base import Venue
from .kalshi_auth import load_private_key_from_env, build_kalshi_headers
from ..core.types import Market, OrderBookSnapshot, Order, Trade, BookLevel
from .ws_client import BaseWSClient

try:  # optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional
    requests = None  # type: ignore

try:  # optional websocket dependency
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # type: ignore


class KalshiVenue(Venue):
    def __init__(
        self,
        name: str = "kalshi",
        base_url: str = "https://api.elections.kalshi.com/trade-api/v2",
        api_key: Optional[str] = None,
        dry_run: bool = True,
        timeout: float = 5.0,
    ):
        super().__init__(name)
        load_dotenv()
        env = (os.getenv("KALSHI_ENV") or "").lower()
        if env == "demo":
            self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        elif env == "prod":
            self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        else:
            self.base_url = base_url
        self.base_url = self.base_url.rstrip("/")
        self.api_key = api_key
        self.dry_run = dry_run
        self.timeout = timeout
        self._last_book: Dict[str, OrderBookSnapshot] = {}
        self._last_api_call = datetime.now()

    def _rate_limit(self, threshold_ms: int = 100) -> None:
        now = datetime.now()
        delta = now - getattr(self, "_last_api_call", now)
        if delta < timedelta(milliseconds=threshold_ms):
            remaining = (timedelta(milliseconds=threshold_ms) - delta).total_seconds()
            if remaining > 0:
                import time as _time

                _time.sleep(min(remaining, 0.25))
        self._last_api_call = datetime.now()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ):
        self._rate_limit()
        url = self.base_url + path
        headers = self._signed_headers(method, path)
        resp = requests.request(method, url, headers=headers, params=params, json=body)
        if not (200 <= resp.status_code < 300):
            raise requests.HTTPError(f"{resp.status_code} {resp.text}")
        return resp.json()

    def verify_auth(self) -> bool:
        if self.dry_run or requests is None:
            return False
        debug = os.getenv("KALSHI_DEBUG") == "1"
        try:
            url = f"{self.base_url}/api_keys"
            headers = self._signed_headers("GET", "/api_keys")
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            ok = 200 <= resp.status_code < 300
            if debug:
                print(f"[kalshi.verify_auth] status={resp.status_code}")
            return ok
        except Exception as e:
            if debug:
                print(f"[kalshi.verify_auth] error: {type(e).__name__}: {e}")
            return False

    def _api_prefix(self) -> str:
        """Return the path prefix from base_url (e.g., '/trade-api/v2').

        Kalshi signing requires TIMESTAMP + METHOD + PATH_WITHOUT_QUERY, where PATH
        should include the '/trade-api/v2' prefix. We derive it from base_url so the
        adapter works for both prod and demo, matching examples/kalshi.
        """
        p = urlparse(self.base_url)
        # Ensure leading slash, no trailing slash
        prefix = (p.path or "/").rstrip("/")
        return prefix if prefix else "/"

    def _headers(self) -> dict:
        """Build headers for Kalshi.

        Supports two modes:
        - Bearer token via api_key for any proxy/gateway setups.
        - Native Kalshi header scheme via env vars (pass-through):
          KALSHI-ACCESS-KEY, KALSHI-ACCESS-SIGNATURE, KALSHI-ACCESS-TIMESTAMP
        We don't compute signatures here; tests can set these values.
        """
        headers: Dict[str, str] = {"Accept": "application/json"}
        # Native Kalshi headers (if provided via env)
        for key in (
            "KALSHI-ACCESS-KEY",
            "KALSHI-ACCESS-SIGNATURE",
            "KALSHI-ACCESS-TIMESTAMP",
        ):
            val = os.getenv(key)
            if val:
                headers[key] = val
        # Fallback to Bearer if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # Automatic signing if key id + private key available and native headers not already set
        if not any(h in headers for h in ("KALSHI-ACCESS-SIGNATURE",)):
            key_id = os.getenv("KALSHI_API_KEY_ID") or headers.get("KALSHI-ACCESS-KEY")
            if key_id:
                priv = load_private_key_from_env()
                if priv is not None:
                    # Build signature for a generic path placeholder later; actual signing done per request
                    headers["KALSHI-ACCESS-KEY"] = key_id
        return headers

    def _signed_headers(self, method: str, path: str) -> dict:
        """Return fully signed headers if private key & key id available.

        path must be the API path portion (e.g. /markets or /markets/{ticker}/orderbook) without base URL or query.
        """
        base = self._headers()
        # If already has signature externally provided, use as-is.
        if "KALSHI-ACCESS-SIGNATURE" in base:
            return base
        key_id = base.get("KALSHI-ACCESS-KEY") or os.getenv("KALSHI_API_KEY_ID")
        priv = load_private_key_from_env()
        if key_id and priv is not None:
            # Prepend the API path prefix (e.g., '/trade-api/v2') to match examples
            prefix = self._api_prefix()
            full_path = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
            signed = build_kalshi_headers(method, full_path, key_id, priv)
            base.update(signed)
        return base

    def list_markets(self) -> Iterable[Market]:
        """Return available markets.

        In dry_run mode or without requests installed, returns an empty list.
        """
        if self.dry_run or requests is None:
            return []
        # Real Kalshi endpoint per OpenAPI: GET /markets
        try:  # pragma: no cover - network avoided in tests
            resp = requests.get(
                f"{self.base_url}/markets",
                headers=self._signed_headers("GET", "/markets"),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []
        # Best-effort mapping; structure is API-dependent.
        markets: List[Market] = []
        for item in data if isinstance(data, list) else data.get("markets", []):
            # Kalshi uses tickers for market identity
            mkt_id = str(item.get("ticker") or item.get("id") or "")
            symbol = item.get("title") or item.get("ticker") or mkt_id
            if mkt_id:
                markets.append(Market(id=mkt_id, symbol=symbol, venue=self.name))
        return markets

    def get_order_book(self, market_id: str) -> OrderBookSnapshot:
        """Return a one-level order book snapshot.

        In dry_run mode returns a synthetic book around 0.50. Real integration
        should call REST/WS and map levels to BookLevel.
        """
        # Serve cached snapshot if available
        cached = self._last_book.get(market_id)
        if cached is not None:
            return cached
        if self.dry_run or requests is None:
            return OrderBookSnapshot(
                market_id=market_id,
                bids=[BookLevel(0.49, 50)],
                asks=[BookLevel(0.51, 50)],
            )
        try:  # pragma: no cover
            # Real Kalshi endpoint per OpenAPI: GET /markets/{ticker}/orderbook
            resp = requests.get(
                f"{self.base_url}/markets/{market_id}/orderbook",
                headers=self._signed_headers("GET", f"/markets/{market_id}/orderbook"),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            ob = resp.json()
        except Exception:
            return OrderBookSnapshot(
                market_id=market_id,
                bids=[BookLevel(0.49, 50)],
                asks=[BookLevel(0.51, 50)],
            )
        # Minimal mapping as a placeholder
        try:
            bids_raw = ob.get("bids") or []
            asks_raw = ob.get("asks") or []

            # Support both list-of-lists [[price, size], ...] and list-of-dicts
            def to_level(x):
                if isinstance(x, (list, tuple)) and len(x) >= 2:
                    return BookLevel(float(x[0]), float(x[1]))
                if isinstance(x, dict):
                    return BookLevel(float(x.get("price", 0)), float(x.get("size", 0)))
                raise ValueError

            bids = [to_level(x) for x in bids_raw][:1]
            asks = [to_level(x) for x in asks_raw][:1]
            if not bids:
                bids = [BookLevel(0.49, 50)]
            if not asks:
                asks = [BookLevel(0.51, 50)]
        except Exception:
            bids = [BookLevel(0.49, 50)]
            asks = [BookLevel(0.51, 50)]
        snap = OrderBookSnapshot(market_id=market_id, bids=bids, asks=asks)
        self._last_book[market_id] = snap
        return snap

    def place_orders(self, orders: List[Order]) -> List[Trade]:
        """Place orders.

        In dry_run mode returns no fills. Real trading requires auth and
        should map execution reports to Trade instances.
        """
        if self.dry_run:
            return []
        raise NotImplementedError(
            "Kalshi trading integration requires auth and is not implemented."
        )

    async def stream_order_books(
        self, market_id: str, interval_s: float = 1.0
    ) -> AsyncIterator[OrderBookSnapshot]:
        """Yield synthetic or real order book snapshots asynchronously.

        Dry-run mode produces a gentle random walk around 0.50. Real mode is
        left as a TODO (would connect to Kalshi WS, subscribe, and parse).
        """
        import random, asyncio

        if self.dry_run or websockets is None:
            mid = 0.50
            while True:
                mid += random.uniform(-0.005, 0.005)
                mid = max(0.01, min(0.99, mid))
                snap = OrderBookSnapshot(
                    market_id=market_id,
                    bids=[BookLevel(round(mid - 0.01, 4), 50)],
                    asks=[BookLevel(round(mid + 0.01, 4), 50)],
                )
                self._last_book[market_id] = snap
                yield snap
                await asyncio.sleep(interval_s)
        else:  # pragma: no cover
            # Minimal WS hookup (ticker feed) to approximate a one-level book.
            import json
            from urllib.parse import urlparse

            p = urlparse(self.base_url)
            ws_scheme = "wss" if p.scheme.startswith("http") else "ws"
            ws_base = f"{ws_scheme}://{p.netloc}"
            ws_path = "/trade-api/ws/v2"

            # Build signed headers for WS path (note: WS uses '/trade-api/ws/v2',
            # not the REST '/trade-api/v2' prefix used above).
            base_headers = self._headers()
            if "KALSHI-ACCESS-SIGNATURE" not in base_headers:
                key_id = base_headers.get("KALSHI-ACCESS-KEY") or os.getenv(
                    "KALSHI_API_KEY_ID"
                )
                priv = load_private_key_from_env()
                if key_id and priv is not None:
                    signed = build_kalshi_headers("GET", ws_path, key_id, priv)
                    base_headers.update(signed)

            url = ws_base + ws_path

            async def _stream_from(ws):
                # Subscribe to ticker channel and filter messages by market_ticker
                msg_id = 1
                sub = {
                    "id": msg_id,
                    "cmd": "subscribe",
                    "params": {"channels": ["ticker"]},
                }
                await ws.send(json.dumps(sub))
                msg_id += 1
                async for raw in ws:
                    try:
                        obj = json.loads(raw)
                    except Exception:
                        continue
                    if obj.get("type") != "ticker":
                        continue
                    m = obj.get("msg") or {}
                    if m.get("market_ticker") != market_id:
                        continue
                    try:
                        yb = float(m.get("yes_bid_dollars") or 0)  # dollars
                        ya = float(m.get("yes_ask_dollars") or 0)
                        if yb <= 0 or ya <= 0 or yb >= ya:
                            continue
                        bids = [BookLevel(yb, 50)]
                        asks = [BookLevel(ya, 50)]
                        snap = OrderBookSnapshot(
                            market_id=market_id, bids=bids, asks=asks
                        )
                        self._last_book[market_id] = snap
                        yield snap
                    except Exception:
                        continue

            # websockets versions vary: try additional_headers (older), then extra_headers, then headers.
            try:
                async with websockets.connect(url, additional_headers=base_headers) as ws:  # type: ignore[arg-type]
                    async for snap in _stream_from(ws):
                        yield snap
            except TypeError:
                try:
                    async with websockets.connect(url, extra_headers=base_headers) as ws:  # type: ignore[arg-type]
                        async for snap in _stream_from(ws):
                            yield snap
                except TypeError:
                    async with websockets.connect(url, headers=base_headers) as ws:  # type: ignore[arg-type]
                        async for snap in _stream_from(ws):
                            yield snap
