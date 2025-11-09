"""In-memory store with optional persistence hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from ..core.types import Market, Inventory


@dataclass
class Store:
    markets: Dict[str, Market] = field(default_factory=dict)
    inventory: Inventory = field(default_factory=Inventory)

    def upsert_market(self, m: Market):
        self.markets[m.id] = m
