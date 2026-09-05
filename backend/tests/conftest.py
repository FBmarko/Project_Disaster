"""Pytest configuration and shared test fixtures."""

import pytest

from app.core.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter_each_test():
    """Reset rate limiter state before each test to maintain test isolation."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()
