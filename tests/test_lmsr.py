from src.pricing.lmsr import LMSR


def test_lmsr_prices_sum_to_one():
    model = LMSR(b=10)
    qs = [0.0, 0.0]
    prices = model.prices(qs)
    assert abs(sum(prices) - 1.0) < 1e-9


def test_lmsr_increases_with_quantity():
    model = LMSR(b=10)
    p_base = model.price_binary(0.0, 0.0)
    p_shift = model.price_binary(50.0, 0.0)
    assert p_shift > p_base
