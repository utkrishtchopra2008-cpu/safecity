"""Bounded in-process sliding-window limits for a single API instance."""

from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowLimiter:
    """Return retry seconds when a key exceeds its configured request window."""

    def __init__(self, *, limit: int, window_seconds: int, max_keys: int = 10_000) -> None:
        if limit < 1 or window_seconds < 1 or max_keys < 1:
            raise ValueError("Rate-limit settings must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, now: float | None = None) -> int | None:
        current = time.monotonic() if now is None else now
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                self._prune(current)
                if len(self._attempts) >= self.max_keys:
                    oldest = min(
                        self._attempts,
                        key=lambda item: (
                            self._attempts[item][-1] if self._attempts[item] else current
                        ),
                    )
                    del self._attempts[oldest]
                attempts = deque()
                self._attempts[key] = attempts
            while attempts and current - attempts[0] >= self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return max(1, self.window_seconds - int(current - attempts[0]))
            attempts.append(current)
            return None

    def _prune(self, now: float) -> None:
        expired = [
            key
            for key, attempts in self._attempts.items()
            if not attempts or now - attempts[-1] >= self.window_seconds
        ]
        for key in expired:
            del self._attempts[key]
