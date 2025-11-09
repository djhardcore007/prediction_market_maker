"""LMSR (Logarithmic Market Scoring Rule) pricing for N outcomes.

Cost function: C(q) = b * log(sum_i exp(q_i / b))
Marginal price p_i = exp(q_i / b) / sum_j exp(q_j / b)
For binary, we often track a single net YES position; here we support general N.
"""

from __future__ import annotations

import math
from typing import Sequence, List

from .base import PricingModel


class LMSR(PricingModel):
    def __init__(self, b: float = 100.0):
        assert b > 0, "b must be positive"
        self.b = b

    def prices(self, quantities: Sequence[float]) -> List[float]:
        # handle empty input gracefully
        if not quantities:
            return []
        # numerical stability: subtract max
        scaled = [q / self.b for q in quantities]
        m = max(scaled)
        exp_scaled = [math.exp(x - m) for x in scaled]
        denom = sum(exp_scaled)
        return [x / denom for x in exp_scaled]

    def cost(self, quantities: Sequence[float]) -> float:
        if not quantities:
            return 0.0
        scaled = [q / self.b for q in quantities]
        m = max(scaled)
        return self.b * (m + math.log(sum(math.exp(x - m) for x in scaled)))

    def price_binary(self, q_yes: float, q_no: float) -> float:
        p_yes, _ = self.prices([q_yes, q_no])
        return p_yes
