"""Entry point for backtests."""

from __future__ import annotations

from .main import build_mock_environment
from ..backtest.engine import run_scenario
from ..backtest.scenarios import random_walk


def main():  # pragma: no cover - manual run
    store, venue, strat = build_mock_environment()
    scenario = random_walk(steps=50, start=0.5, sigma=0.03, seed=42)
    run_scenario(store, venue, strat, scenario)
    print("Backtest done. Final net YES:", store.inventory.net_yes("YES_2025_EVENT"))


if __name__ == "__main__":  # pragma: no cover
    main()
