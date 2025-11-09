import os
import pytest

from src.venue.kalshi import KalshiVenue

from dotenv import load_dotenv  # type: ignore

load_dotenv()
LIVE = os.getenv("LIVE_API") == "1"


pytestmark = pytest.mark.skipif(
    not LIVE, reason="LIVE_API=1 not set; skipping external integration tests"
)


def _first(iterable):
    for x in iterable:
        return x
    return None


def test_live_kalshi_markets_and_one_order_book():
    v = KalshiVenue(dry_run=False)
    markets = list(v.list_markets())
    if not markets:
        import pytest as _pytest

        _pytest.skip("Kalshi returned zero markets (network/creds?)")
    m = _first(markets)
    ob = v.get_order_book(m.id)
    assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price


def test_live_kalshi_stream_order_books_minimal():
    """Integration: connect WS and collect a few snapshots for a real market.

    Skips if auth isn't configured or if no ticker data arrives within timeout.
    """
    try:
        import websockets as _ws  # noqa: F401
    except Exception:
        pytest.skip("websockets not installed")

    v = KalshiVenue(dry_run=False, timeout=5.0)
    if not v.verify_auth():
        pytest.skip("Kalshi auth not configured; skipping live WS stream test")

    markets = list(v.list_markets())
    if not markets:
        pytest.skip("Kalshi returned zero markets (network/creds?)")
    market_id = markets[0].id

    import asyncio

    async def _collect_n():
        out = []
        async for ob in v.stream_order_books(market_id, interval_s=0.05):
            out.append(ob)
            if len(out) >= 3:
                break
        return out

    try:
        items = asyncio.run(asyncio.wait_for(_collect_n(), timeout=15.0))
    except asyncio.TimeoutError:
        pytest.skip("No ticker updates received within timeout; skipping")

    assert items, "expected at least one book from WS stream"
    for ob in items:
        assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price
