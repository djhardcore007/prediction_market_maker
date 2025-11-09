<div align="left">

# Prediction Market Maker

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
[![CI](https://img.shields.io/badge/Tests-pytest%20%2B%20coverage-brightgreen.svg)](#testing)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![Package: uv](https://img.shields.io/badge/installer-uv-purple.svg)](https://github.com/astral-sh/uv)

</div>

Modular, testable market making toolkit for binary prediction markets. Supports hybrid orderbook and AMM venue abstractions, inventory-aware pricing, and reproducible backtests.

## Features

| Domain | Capabilities |
| ------ | ------------ |
| Venue | Unified interface for orderbook & pool (AMM) venues; mock venue for simulation |
| Pricing | LMSR, CPMM (planned), inventory skew helpers |
| Strategy | Binary MM with spread + inventory adjustment; pluggable strategy base |
| Risk | Position & notional limits, kill switch, exposure metrics |
| Execution | Simple router + rate throttle |
| State | Rolling book snapshots, inventory tracking |
| Backtest | Scenario generators (random walk), engine loop |
| Instrumentation | Optional Prometheus metrics, persistence hooks |

## Architecture Overview

```
src/
   core/        # types, events, utilities
   pricing/     # models (LMSR, CPMM), inventory skew
   strategy/    # abstract + concrete MM strategies
   venue/       # adapters: mock + (kalshi, polymarket stubs)
   risk/        # limits, kill switch, exposure helpers
   exec/        # routing & throttling
   state/       # store + rolling book
   backtest/    # scenarios + engine
   io/          # metrics + persistence
   app/         # bootstrap scripts for live/backtest
tests/         # unit tests (pricing, strategy, risk)
docs/          # tutorials & guides
```

Design principles:
1. Separation of concerns (strategy vs pricing vs venue).
2. Pure functions/dataclasses where possible for clarity/testing.
3. Explicit risk + metrics hooks for production hardening.
4. Small surface area for extension (implement one abstract base, register).

## Quick Start

### Using Makefile (recommended)

```bash
brew install uv              # ensure uv available
make all                     # create venv, install deps, lint, format, test
make test                    # run tests w/ coverage
make cov                     # coverage report
make lint                    # mypy + optional checks
make fmt                     # black formatting
```

### Manual Setup

```bash
uv venv --python /opt/homebrew/opt/python@3.11/bin/python3.11 .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q --cov=prediction_market_maker
```

## Usage Example

```python
from prediction_market_maker.strategy.binary_mm import BinaryMMStrategy
from prediction_market_maker.core.types import OrderBookSnapshot, BookLevel

strat = BinaryMMStrategy(spread_bps=80)
book = OrderBookSnapshot(
      market_id="EVT", bids=[BookLevel(0.49, 100)], asks=[BookLevel(0.51, 100)]
)
orders = strat.quote(book)
for o in orders:
      print(o.side, o.price, o.qty)
```

## Testing & Coverage

Tests use `pytest` with `pytest-cov` for coverage. Run:

```bash
make test
```

This produces a term-missing report to highlight gaps; prioritize core logic first (strategy, pricing) then ancillary utilities.

## Code Quality

- Formatting: `black`
- Type checking: `mypy`
- Linting target: keep modules small, favor dataclasses & pure functions
- Optional metrics: Prometheus counters guarded by import checks

## Extending

| To add | Implement | File |
| ------ | --------- | ---- |
| New venue | subclass `Venue` | `src/venue/base.py` |
| Pricing model | subclass `PricingModel` | `src/pricing/base.py` |
| Strategy | subclass `Strategy` | `src/strategy/base.py` |
| Risk control | add methods / dataclasses | `src/risk/*` |
| Metric | create counter/gauge w/ fallback | `src/io/metrics.py` |

## Roadmap

- Finish CPMM model
- Add orderbook depth simulation
- More scenarios (mean reversion, jump events)
- PnL attribution & reporting module
- CLI for venue + strategy selection

## License

MIT. See `LICENSE`.
