"""Strategy base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..core.types import Order, OrderBookSnapshot


class Strategy(ABC):
    @abstractmethod
    def quote(self, book: OrderBookSnapshot) -> List[Order]: ...
