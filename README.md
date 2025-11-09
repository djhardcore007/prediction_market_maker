# Prediction Market Maker

Modular market maker toolkit for prediction markets supporting orderbook and AMM venues.

## Goals

- Unified abstraction for venues (orderbook + AMM)
- Pluggable pricing models (LMSR, CPMM, inventory-aware spreads)
- Strategies adaptable to inventory, microstructure, and risk limits
- Backtesting engine + reproducible scenarios
- Simple risk layer (limits, exposure, kill switch)
- Metrics & persistence hooks

## Project Layout
```
prediction_market_maker/
├─ pyproject.toml
├─ src/
│  ├─ config/
│  │  └─ default.yaml
│  ├─ core/
│  │  ├─ types.py
│  │  ├─ events.py
│  │  ├─ utils.py
│  │  └─ clock.py
│  ├─ venue/
│  │  ├─ base.py
│  │  ├─ polymarket.py
│  │  ├─ kalshi.py
│  │  └─ mock.py
│  ├─ pricing/
│  │  ├─ base.py
│  │  ├─ lmsr.py
│  │  ├─ cpmm.py
│  │  └─ inventory.py
│  ├─ strategy/
│  │  ├─ base.py
│  │  ├─ binary_mm.py
│  │  └─ amm_liquidity.py
│  ├─ risk/
│  │  ├─ limits.py
│  │  ├─ exposure.py
│  │  └─ kill_switch.py
│  ├─ exec/
│  │  ├─ router.py
│  │  └─ throttle.py
│  ├─ state/
│  │  ├─ book.py
│  │  └─ store.py
│  ├─ io/
│  │  ├─ metrics.py
│  │  └─ persistence.py
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ run_live.py
│  │  └─ run_backtest.py
│  └─ backtest/
│     ├─ engine.py
│     └─ scenarios.py
└─ tests/
   ├─ test_lmsr.py
   ├─ test_strategy.py
   └─ test_risk.py
```

## Quick Start

```bash
# from repo root using uv (recommended)
brew install uv            # if not already installed
make all                   # make all
make venv                  # creates .venv with Homebrew Python via uv
make install               # editable install + dev deps via uv
make test                  # run tests with coverage

# Or manual uv without Makefile:
uv venv --python /opt/homebrew/opt/python@3.11/bin/python3.11 .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q
```

## Extending
- Implement a new venue: subclass `Venue` in `venue/base.py`.
- Add pricing: subclass `PricingModel` in `pricing/base.py`.
- Strategy logic: subclass `Strategy` in `strategy/base.py`.

## License
MIT
