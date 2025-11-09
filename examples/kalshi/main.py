"""Example runner for Kalshi clients.

Reads .env (if present) and uses KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH.
Set KALSHI_ENV=demo|prod to switch environments (default demo).
Falls back to a tiny .env parser if python-dotenv isn't installed.
"""
from __future__ import annotations

import os
import asyncio

from .clients import Environment, load_private_key, KalshiHttpClient, KalshiWebSocketClient


def safe_load_dotenv() -> None:
    """Load environment variables from .env if available.

    Tries python-dotenv; if not installed, falls back to a tiny parser.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
        return
    except Exception:
        pass
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        # non-fatal
        return


def get_env() -> Environment:
    env = (os.getenv("KALSHI_ENV") or "demo").lower()
    return Environment.DEMO if env == "demo" else Environment.PROD


def main():
    safe_load_dotenv()
    env = get_env()
    key_id = os.getenv("KALSHI_API_KEY_ID")
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if not key_id or not key_path:
        raise SystemExit("Set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH in your environment")

    pk = load_private_key(key_path)

    http = KalshiHttpClient(key_id=key_id, private_key=pk, environment=env)
    status = http.get_exchange_status()
    print(f"Environment: {env.value} | Exchange status: {status}")

    tried_alt = False
    alt_env = env
    try:
        bal = http.get_balance()
        print("Balance:", bal)
    except Exception as exc:
        print("Balance call failed (requires auth tier):", exc)
        # If auth fails in this environment, try once with the alternate environment and hint the user.
        # Quick auth probe to suggest env flip
        if not http.verify_auth():
            alt_env = Environment.PROD if env == Environment.DEMO else Environment.DEMO
            alt_http = http.with_environment(alt_env)
            if alt_http.verify_auth():
                tried_alt = True
                print(f"Hint: Your API key looks valid in '{alt_env.value}'. Set KALSHI_ENV={alt_env.value} and retry.")
            else:
                print("Hint: 401 usually means the key/private key pair doesn't exist in this environment or lacks required access.\n- Check KALSHI_API_KEY_ID and private key match\n- Ensure you created the key in this environment (demo vs prod)\n- Confirm your account has API access for portfolio endpoints.")

    ws_env = alt_env if tried_alt else env
    ws = KalshiWebSocketClient(key_id=key_id, private_key=pk, environment=ws_env)
    try:
        # If we already detected the alternate env, connect directly there. Otherwise allow a one-shot retry.
        asyncio.run(ws.connect(retry_with_alternate_env=not tried_alt))
    except Exception as exc:
        print("WebSocket connect failed:", exc)
        print("If this is a 401, it's typically an environment mismatch or insufficient API permissions.")


if __name__ == "__main__":
    main()
