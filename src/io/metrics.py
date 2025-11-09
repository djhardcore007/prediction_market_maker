"""Metrics instrumentation (placeholder)."""

from __future__ import annotations

from typing import Any, Optional

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter as _PromCounter
except ImportError:  # pragma: no cover
    _PromCounter = None  # type: ignore

orders_total: Optional[Any]
if _PromCounter is not None:
    orders_total = _PromCounter("orders_total", "Total orders routed")
else:
    orders_total = None


def inc_orders(n: int = 1) -> None:
    if orders_total is not None:  # explicit None check avoids mypy truthiness warning
        orders_total.inc(n)
