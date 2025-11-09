"""Pricing model abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class PricingModel(ABC):
    @abstractmethod
    def prices(self, quantities: Sequence[float]) -> Sequence[float]:
        """Return marginal prices for each outcome given current outstanding quantity vector."""
        ...
