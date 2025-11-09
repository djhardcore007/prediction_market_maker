"""Minimal Kalshi HTTP + WebSocket clients using RSA signing.

This example mirrors the starter code structure but reuses the shared signing
helper from the library (`src/venue/kalshi_auth.py`). It does NOT depend on the
internal adapter classes so you can see raw calls and adapt to custom flows.

Environment selection:
- DEMO: https://demo-api.kalshi.co
- PROD: https://api.elections.kalshi.com

Signing:
Concatenate TIMESTAMP(ms) + METHOD + PATH_WITHOUT_QUERY and sign with RSA-PSS.
"""
from __future__ import annotations

import os
import time
import json
import base64
import asyncio
from enum import Enum
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests
import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Reuse shared loader from our package if desired; fallback manual load below.
try:
    from src.venue.kalshi_auth import load_private_key_from_env as _load_pk
except Exception:  # pragma: no cover
    _load_pk = None


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"


def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


class KalshiBaseClient:
    def __init__(self, key_id: str, private_key, environment: Environment = Environment.DEMO):
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()
        if environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        else:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"

    def _timestamp_ms(self) -> str:
        return str(int(time.time() * 1000))

    def _sign(self, msg: str) -> str:
        signature = self.private_key.sign(
            msg.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def auth_headers(self, method: str, path: str) -> Dict[str, str]:
        ts = self._timestamp_ms()
        canonical = ts + method.upper() + path.split("?")[0]
        sig = self._sign(canonical)
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig,
        }


class KalshiHttpClient(KalshiBaseClient):
    def __init__(self, key_id: str, private_key, environment: Environment = Environment.DEMO):
        super().__init__(key_id, private_key, environment)
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"

    def with_environment(self, env: Environment):
        """Return a shallow-cloned client targeting a different environment."""
        return KalshiHttpClient(self.key_id, self.private_key, environment=env)

    def _rate_limit(self):
        threshold_ms = 100
        now = datetime.now()
        if (now - self.last_api_call) < timedelta(milliseconds=threshold_ms):
            time.sleep(threshold_ms / 1000)
        self.last_api_call = datetime.now()

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None):
        self._rate_limit()
        url = self.HTTP_BASE_URL + path
        headers = self.auth_headers(method, path)
        resp = requests.request(method, url, headers=headers, params=params, json=body)
        if not (200 <= resp.status_code < 300):
            raise requests.HTTPError(f"{resp.status_code} {resp.text}")
        return resp.json()

    def get_balance(self) -> Dict[str, Any]:
        return self._request("GET", self.portfolio_url + "/balance")

    def get_exchange_status(self) -> Dict[str, Any]:
        return self._request("GET", self.exchange_url + "/status")

    def get_markets(self, limit: int = 50) -> Dict[str, Any]:
        return self._request("GET", self.markets_url, params={"limit": limit})

    def get_trades(self, ticker: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {"ticker": ticker, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        return self._request("GET", self.markets_url + "/trades", params=params)

    def verify_auth(self) -> bool:
        """Best-effort check to see if credentials are valid in this environment.

        Uses a lightweight authenticated endpoint. Returns False on 401/403.
        """
        try:
            # /api_keys is small and requires auth
            self._request("GET", "/trade-api/v2/api_keys")
            return True
        except requests.HTTPError as e:  # type: ignore[attr-defined]
            txt = str(e)
            if " 401 " in txt or " 403 " in txt:
                return False
            return False
        except Exception:
            return False


class KalshiWebSocketClient(KalshiBaseClient):
    def __init__(self, key_id: str, private_key, environment: Environment = Environment.DEMO):
        super().__init__(key_id, private_key, environment)
        self.url_suffix = "/trade-api/ws/v2"
        self.ws = None
        self._msg_id = 1

    async def connect(self, *, retry_with_alternate_env: bool = True):
        host = self.WS_BASE_URL + self.url_suffix
        headers = self.auth_headers("GET", self.url_suffix)
        try:
            async with websockets.connect(host, additional_headers=headers) as ws:
                self.ws = ws
                await self._on_open()
                await self._handler()
        except websockets.exceptions.InvalidStatus as e:  # type: ignore[attr-defined]
            # 401s are commonly caused by wrong environment for the key
            status = getattr(e, "response", None)
            code = getattr(status, "status_code", None) if status else None
            if retry_with_alternate_env and (code == 401 or True):
                alt = Environment.PROD if self.environment == Environment.DEMO else Environment.DEMO
                print(f"WS 401 in {self.environment.value}; retrying once with {alt.value}...")
                alt_client = KalshiWebSocketClient(self.key_id, self.private_key, environment=alt)
                await alt_client.connect(retry_with_alternate_env=False)
            else:
                raise
        except Exception:
            raise

    async def _on_open(self):
        print("WS opened")
        await self.subscribe(["ticker"])  # subscribe to ticker channel

    async def subscribe(self, channels):
        msg = {"id": self._msg_id, "cmd": "subscribe", "params": {"channels": channels}}
        await self.ws.send(json.dumps(msg))
        self._msg_id += 1

    async def _handler(self):
        try:
            async for raw in self.ws:
                print("WS message:", raw)
        except websockets.ConnectionClosed as e:
            print("WS closed", e.code, e.reason)
        except Exception as exc:
            print("WS error", exc)


def bootstrap_from_env(environment: Environment = Environment.DEMO) -> KalshiHttpClient:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if not key_id or not path:
        raise RuntimeError("KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH must be set in env")
    private_key = _load_pk().private_key if _load_pk and os.getenv("KALSHI_PRIVATE_KEY") else load_private_key(path)
    return KalshiHttpClient(key_id=key_id, private_key=private_key, environment=environment)
