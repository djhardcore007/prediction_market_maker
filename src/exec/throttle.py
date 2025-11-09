"""Basic rate limiter (token bucket)."""

from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, rate_per_s: float, capacity: float | None = None):
        self.rate = rate_per_s
        self.capacity = capacity or rate_per_s
        self.tokens = self.capacity
        self.timestamp = time.time()

    def allow(self, tokens: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.timestamp
        self.timestamp = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
