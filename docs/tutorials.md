# Prediction Market Maker: Tutorials

Welcome! This tutorial gives you a fast tour of the codebase and shows how to run a simple backtest and a live mock loop.

## Overview

The project follows a clean, modular src/ layout:

- core/: foundational types (Order, Trade, Market, OrderBookSnapshot), utilities, clock
- venue/: exchange adapters
  - base.py: abstract interface
  - mock.py: simple one-level book used in backtests
- pricing/: pricing engines and helpers
  - lmsr.py: LMSR model (N outcomes)
  - inventory.py: inventory-aware skew
- strategy/: strategy contract and implementations
  - binary_mm.py: simple binary market-maker using LMSR + inventory skew
- risk/: basic limits, exposure metrics, kill switch
- exec/: order routing and throttling
- state/: book and store (in-memory)
- app/: wiring and entry points for backtest/live
- backtest/: minimal scenario engine + scenarios

Tests live under tests/ and exercise LMSR, strategy quoting, and risk.

## Data flow (high level)

1. A Venue (e.g., MockVenue) provides market listings and order book snapshots.
2. A Strategy consumes an OrderBookSnapshot and produces quotes (list of Orders).
3. The Router sends orders to the chosen Venue.
4. The Venue returns Trades reflecting fills (IOC-style in mock).
5. The Store updates Inventory based on Trades; Risk/metrics may be consulted.

## Quick start

Use the Makefile (uv-based) from repo root:

```bash
make all       # venv + install + lint + fmt + test
make cov       # generate HTML coverage report
```

Alternatively, manual uv:

```bash
uv venv --python /opt/homebrew/opt/python@3.11/bin/python3.11 .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q
```

## Backtest example

```python
# examples/backtest_demo.py (not in repo by default)
from src.app.main import build_mock_environment
from src.backtest.engine import run_scenario
from src.backtest.scenarios import random_walk

store, venue, strat = build_mock_environment()
scenario = random_walk(steps=50, start=0.5, sigma=0.03, seed=42)
run_scenario(store, venue, strat, scenario)
print("Final net YES:", store.inventory.net_yes("YES_2025_EVENT"))
```

Or run the built-in entry point:

```bash
python -m src.app.run_backtest
```

## Live mock loop

```bash
python -m src.app.run_live
```

This connects to MockVenue, posts quotes, and updates inventory.

## Implementation notes and best practices

- Strategy spread: `BinaryMMStrategy` treats `spread_bps` as total spread; it allocates half per side and rounds bid/ask to tick using floor/ceil so the spread never collapses.
- LMSR: implements a numerically stable softmax. Empty input is handled gracefully.
- Rounding: `core.utils.floor_to_tick` and `ceil_to_tick` avoid banker's rounding pitfalls.
- Optional metrics: `io.metrics` works even without `prometheus_client` installed (no-op).
- Tests: kept minimal but demonstrate the contract. Extend with more edge cases as needed.

## Extending the system

- New Venue: subclass `venue.base.Venue` and implement `list_markets`, `get_order_book`, and `place_orders`.
- New Strategy: subclass `strategy.base.Strategy` and implement `quote`.
- New Pricing: subclass `pricing.base.PricingModel` and implement `prices`; add helpers/tests.
- Risk: evolve `risk.limits` and `risk.kill_switch` to your needs (per-venue caps, drawdown, etc.).

## Troubleshooting

- Import errors during tests: pytest is configured to include the repository root on sys.path; tests import modules as `from src...`.
- Python version: Makefile pins to Homebrew Python 3.11; adjust `PY` in the Makefile if needed.
- uv missing: `brew install uv`.

## Next steps

- Add integration adapters for real venues.
- Expand backtest engine (latency, adverse selection, inventory PnL).
- Add CI (GitHub Actions) with uv, pytest, coverage, mypy.
