import asyncio

from src.venue.kalshi import KalshiVenue
from src.venue.polymarket import PolymarketVenue


async def _collect_n(async_iter, n):
    out = []
    async for item in async_iter:
        out.append(item)
        if len(out) >= n:
            break
    return out


def test_kalshi_stream_dry_run_produces_books():
    v = KalshiVenue(dry_run=True)
    items = asyncio.run(_collect_n(v.stream_order_books("EVT", interval_s=0.01), 3))
    assert len(items) == 3
    for ob in items:
        assert ob.bids[0].price < ob.asks[0].price


def test_polymarket_stream_dry_run_produces_books():
    v = PolymarketVenue(dry_run=True)
    items = asyncio.run(_collect_n(v.stream_order_books("EVT", interval_s=0.01), 3))
    assert len(items) == 3
    for ob in items:
        assert ob.bids[0].price < ob.asks[0].price
