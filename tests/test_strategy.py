from src.strategy.binary_mm import BinaryMMStrategy
from src.core.types import OrderBookSnapshot, BookLevel


def test_binary_mm_quotes_two_orders():
    strat = BinaryMMStrategy(spread_bps=100)
    book = OrderBookSnapshot(
        market_id="M", bids=[BookLevel(0.49, 100)], asks=[BookLevel(0.51, 100)]
    )
    orders = strat.quote(book)
    assert len(orders) == 2
    bid = [o for o in orders if o.side.name == "BUY"][0]
    ask = [o for o in orders if o.side.name == "SELL"][0]
    assert bid.price < ask.price
