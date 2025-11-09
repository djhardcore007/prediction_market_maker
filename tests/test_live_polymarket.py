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
