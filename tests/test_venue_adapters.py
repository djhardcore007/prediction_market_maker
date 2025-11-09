from src.venue.kalshi import KalshiVenue
from src.venue.polymarket import PolymarketVenue


def test_kalshi_dry_run_lists_no_markets():
    v = KalshiVenue(dry_run=True)
    assert list(v.list_markets()) == []


def test_kalshi_dry_run_order_book():
    v = KalshiVenue(dry_run=True)
    ob = v.get_order_book("TEST")
    assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price


def test_polymarket_dry_run_lists_no_markets():
    v = PolymarketVenue(dry_run=True)
    assert list(v.list_markets()) == []


def test_polymarket_dry_run_order_book():
    v = PolymarketVenue(dry_run=True)
    ob = v.get_order_book("TEST")
    assert ob.bids and ob.asks and ob.bids[0].price < ob.asks[0].price
