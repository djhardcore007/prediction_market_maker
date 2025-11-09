"""Shared minimal WebSocket client with safe defaults.

This avoids hard-coding provider-specific payloads. It offers:
- Async connect context manager
- Subscribe / unsubscribe helpers (JSON payloads)
- Message iterator with JSON parsing and error handling

Real schemas vary by venue; pass appropriate payloads and parse messages
in the adapter.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

try:  # optional dependency
    import websockets  # type: ignore
    from websockets.client import WebSocketClientProtocol  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # type: ignore
    WebSocketClientProtocol = object  # type: ignore

import asyncio
import json


class BaseWSClient:
    _ws: Optional[WebSocketClientProtocol]

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        subscribe_template: Optional[Dict[str, Any]] = None,
        unsubscribe_template: Optional[Dict[str, Any]] = None,
        markets_field: str = "market_id",
        markets_array_field: Optional[str] = None,
    ):
        """Create a client.

        - subscribe_template / unsubscribe_template will be deep-copied and filled
          with market ids under either `markets_array_field` (list) or `markets_field`
          (single id) depending on which is set.
        """
        self.url = url
        self.headers = headers or {}
        self.subscribe_template = subscribe_template or {}
        self.unsubscribe_template = unsubscribe_template or {}
        self.markets_field = markets_field
        self.markets_array_field = markets_array_field
        self._ws = None

    async def __aenter__(self) -> "BaseWSClient":
        if websockets is None:
            raise RuntimeError("websockets package not installed")
        self._ws = await websockets.connect(self.url, extra_headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    async def subscribe(self, market_ids: Iterable[str]) -> None:
        if self._ws is None:
            raise RuntimeError("WS not connected")
        payload = json.loads(json.dumps(self.subscribe_template))  # deep copy
        ids = list(market_ids)
        if self.markets_array_field:
            payload[self.markets_array_field] = ids
        else:
            payload[self.markets_field] = ids[0] if ids else None
        await self._ws.send(json.dumps(payload))

    async def unsubscribe(self, market_ids: Iterable[str]) -> None:
        if self._ws is None:
            raise RuntimeError("WS not connected")
        payload = json.loads(json.dumps(self.unsubscribe_template))
        ids = list(market_ids)
        if self.markets_array_field:
            payload[self.markets_array_field] = ids
        else:
            payload[self.markets_field] = ids[0] if ids else None
        await self._ws.send(json.dumps(payload))

    async def messages(self) -> AsyncIterator[Dict[str, Any]]:
        if self._ws is None:
            raise RuntimeError("WS not connected")
        while True:
            try:
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    # try to decode bytes to text
                    raw = raw.decode("utf-8", errors="ignore")
                msg = json.loads(raw)
                if isinstance(msg, dict):
                    yield msg
                else:
                    # ignore non-dict messages
                    continue
            except json.JSONDecodeError:
                # ignore malformed JSON and continue
                continue
            except asyncio.CancelledError:
                raise
            except Exception:
                # transient failure: break loop to allow outer reconnect logic
                break
