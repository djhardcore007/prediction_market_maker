"""Kalshi RSA-PSS signing helper.

Generates the required headers for Kalshi's Trade API:
- KALSHI-ACCESS-KEY: API key ID (a GUID-like string shown in the UI)
- KALSHI-ACCESS-TIMESTAMP: milliseconds since epoch
- KALSHI-ACCESS-SIGNATURE: base64-encoded RSA-PSS(SHA256) signature over
  timestamp + HTTP_METHOD + PATH_WITHOUT_QUERY

Provide either the PEM contents or a file path via env; use helpers below.
"""

from __future__ import annotations

from typing import Dict, Optional, Any
import base64
import datetime as _dt
import os

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.backends import default_backend
except Exception:  # pragma: no cover - optional dependency
    hashes = None  # type: ignore
    serialization = None  # type: ignore
    padding = None  # type: ignore
    rsa = None  # type: ignore
    default_backend = None  # type: ignore


def _load_private_key_from_pem(pem: bytes):
    if serialization is None:
        raise RuntimeError("cryptography is not installed; cannot sign Kalshi requests")
    return serialization.load_pem_private_key(
        pem, password=None, backend=default_backend()
    )


def load_private_key_from_env() -> Optional[Any]:
    """Load PEM from either KALSHI_PRIVATE_KEY (PEM content) or KALSHI_PRIVATE_KEY_PATH.

    Returns None if neither is provided.
    """
    pem_env = os.getenv("KALSHI_PRIVATE_KEY")
    path: Optional[str] = None
    if pem_env and pem_env.strip():
        # If the env contains literal PEM, use it. Otherwise, treat as path.
        text = pem_env.strip()
        if text.startswith("-----BEGIN"):
            return _load_private_key_from_pem(text.encode("utf-8"))
        # Fallback: assume it's a path
        path = text
    else:
        path = os.getenv("KALSHI_PRIVATE_KEY_PATH")

    if path:
        with open(path, "rb") as f:
            pem = f.read()
        return _load_private_key_from_pem(pem)
    return None


def sign_pss_text(private_key: Any, text: str) -> str:
    if hashes is None or padding is None:
        raise RuntimeError("cryptography is not installed; cannot sign Kalshi requests")
    signature = private_key.sign(
        text.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def build_kalshi_headers(
    method: str, path_without_query: str, key_id: str, private_key: Any
) -> Dict[str, str]:
    ts_ms = int(_dt.datetime.now().timestamp() * 1000)
    ts_str = str(ts_ms)
    msg = f"{ts_str}{method.upper()}{path_without_query}"
    sig = sign_pss_text(private_key, msg)
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts_str,
    }
