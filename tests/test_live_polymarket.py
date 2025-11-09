import os
import pytest
from dotenv import load_dotenv  # type: ignore
from src.venue.polymarket import PolymarketVenue

load_dotenv()
LIVE = os.getenv("LIVE_API") == "1"

# Enforce live-only execution; do not fall back to synthetic dry-run.
pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="LIVE_API=1 not set; skipping external Polymarket integration tests",
)


def _first(iterable):
    for x in iterable:
        return x
    return None


def test_live_polymarket_markets_and_one_order_book():
    v = PolymarketVenue(dry_run=False)
    markets = list(v.list_markets())
    if not markets:
        pytest.skip("Polymarket returned zero markets (network/creds?)")
    m = _first(markets)
    ob = v.get_order_book(m.id)
    assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price


def test_live_polymarket_stream_order_books_minimal():
    """Integration: connect WS MARKET channel and collect a few snapshots.

    Skips if websockets isn't installed, no numeric asset id is available,
    or if no updates arrive within timeout.
    """
    try:
        import websockets as _ws  # noqa: F401
    except Exception:
        pytest.skip("websockets not installed")

    v = PolymarketVenue(dry_run=False, timeout=5.0)

    markets = list(v.list_markets())
    if not markets:
        pytest.skip("Polymarket returned zero markets (network/creds?)")

    # Prefer explicit asset id via env; else pick first numeric market id
    asset_id = os.getenv("POLYMARKET_ASSET_ID")
    if not asset_id:
        for m in markets:
            if str(m.id).isdigit():
                asset_id = m.id
                break
    if not asset_id:
        pytest.skip(
            "No numeric asset id found; set POLYMARKET_ASSET_ID to test WS stream"
        )

    import asyncio

    async def _collect_n():
        out = []
        async for ob in v.stream_order_books(asset_id, interval_s=0.05):
            out.append(ob)
            if len(out) >= 3:
                break
        return out

    try:
        items = asyncio.run(asyncio.wait_for(_collect_n(), timeout=15.0))
    except asyncio.TimeoutError:
        pytest.skip("No book updates received within timeout; skipping")

    assert items, "expected at least one book from WS stream"
    for ob in items:
        assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price
