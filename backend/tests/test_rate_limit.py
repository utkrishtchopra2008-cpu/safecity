from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.sources import _enforce_user_limit
from app.core.rate_limit import SlidingWindowLimiter


def test_sliding_window_returns_retry_after_then_recovers() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)

    assert limiter.check("user-a", now=100.0) is None
    assert limiter.check("user-a", now=110.0) is None
    assert limiter.check("user-a", now=115.0) == 45
    assert limiter.check("user-b", now=115.0) is None
    assert limiter.check("user-a", now=160.0) is None


def test_limiter_bounds_key_memory_by_pruning_and_eviction() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10, max_keys=2)

    assert limiter.check("old", now=0.0) is None
    assert limiter.check("active", now=8.0) is None
    assert limiter.check("new", now=9.0) is None
    assert len(limiter._attempts) <= 2
    assert limiter.check("active", now=9.5) == 9


@pytest.mark.parametrize(("limit", "window", "max_keys"), [(0, 5, 10), (2, 0, 10), (2, 5, 0)])
def test_limiter_rejects_invalid_settings(limit: int, window: int, max_keys: int) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        SlidingWindowLimiter(limit=limit, window_seconds=window, max_keys=max_keys)


def test_source_mutation_limit_returns_safe_retry_after() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    user_id = uuid4()

    _enforce_user_limit(limiter, user_id)
    with pytest.raises(HTTPException) as error:
        _enforce_user_limit(limiter, user_id)

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}
    assert "secret" not in str(error.value.detail).lower()
