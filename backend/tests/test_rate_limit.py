"""Unit tests for in-memory sliding-window rate limiter."""

import threading

from app.core.rate_limit import SlidingWindowRateLimiter, get_client_ip


class MockClock:
    """Deterministic injectable clock for testing rate limiter windows."""

    def __init__(self, initial_time: float = 1000.0) -> None:
        self.current_time = initial_time

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


def test_rate_limiter_allows_requests_below_limit() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    for _ in range(4):
        allowed, retry_after = limiter.check_and_record(
            "client_1", max_requests=5, window_seconds=60
        )
        assert allowed is True
        assert retry_after == 0


def test_rate_limiter_allows_exact_limit() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    for _ in range(5):
        allowed, retry_after = limiter.check_and_record(
            "client_1", max_requests=5, window_seconds=60
        )
        assert allowed is True
        assert retry_after == 0


def test_rate_limiter_rejects_above_limit_with_retry_after() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    for _ in range(5):
        allowed, _ = limiter.check_and_record(
            "client_1", max_requests=5, window_seconds=60
        )
        assert allowed is True

    # 6th request is rejected
    allowed, retry_after = limiter.check_and_record(
        "client_1", max_requests=5, window_seconds=60
    )
    assert allowed is False
    assert retry_after == 60


def test_rate_limiter_independent_buckets_per_client() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    # Client A exhausts quota
    for _ in range(3):
        allowed, _ = limiter.check_and_record(
            "client_a", max_requests=3, window_seconds=60
        )
        assert allowed is True

    allowed_a, _ = limiter.check_and_record(
        "client_a", max_requests=3, window_seconds=60
    )
    assert allowed_a is False

    # Client B still has full quota
    for _ in range(3):
        allowed_b, _ = limiter.check_and_record(
            "client_b", max_requests=3, window_seconds=60
        )
        assert allowed_b is True


def test_rate_limiter_sliding_window_expiration() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    # 2 requests at t = 1000
    limiter.check_and_record("client_1", max_requests=2, window_seconds=60)
    limiter.check_and_record("client_1", max_requests=2, window_seconds=60)

    # Rejected at t = 1000
    allowed, retry_after = limiter.check_and_record(
        "client_1", max_requests=2, window_seconds=60
    )
    assert allowed is False
    assert retry_after == 60

    # Advance clock 30 seconds -> still blocked
    clock.advance(30.0)
    allowed, retry_after = limiter.check_and_record(
        "client_1", max_requests=2, window_seconds=60
    )
    assert allowed is False
    assert retry_after == 30

    # Advance clock past 60 seconds (total 61s) -> window slides, allowed again
    clock.advance(31.0)
    allowed, retry_after = limiter.check_and_record(
        "client_1", max_requests=2, window_seconds=60
    )
    assert allowed is True
    assert retry_after == 0


def test_rate_limiter_stale_bucket_cleanup() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    limiter.check_and_record("old_client", max_requests=5, window_seconds=60)
    assert "old_client" in limiter._buckets

    # Advance time past window (61 seconds)
    clock.advance(61.0)

    # Trigger cleanup: purges expired bucket
    deleted = limiter.cleanup_stale()
    assert deleted == 1
    assert "old_client" not in limiter._buckets


def test_rate_limiter_window_aware_cleanup_does_not_purge_valid_long_window() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    # 600-second window
    limiter.check_and_record("long_client", max_requests=5, window_seconds=600)
    assert "long_client" in limiter._buckets

    # Advance past arbitrary 300 seconds (e.g. 350s)
    clock.advance(350.0)

    # Cleanup must NOT purge this bucket because timestamps are still valid
    deleted = limiter.cleanup_stale()
    assert deleted == 0
    assert "long_client" in limiter._buckets

    # Now advance past 600 seconds (total 601s)
    clock.advance(251.0)
    deleted = limiter.cleanup_stale()
    assert deleted == 1
    assert "long_client" not in limiter._buckets


def test_rate_limiter_hard_max_keys_cap_fails_closed() -> None:
    clock = MockClock()
    # Tiny capacity of 2 keys
    limiter = SlidingWindowRateLimiter(time_func=clock.time, max_keys=2)

    # Client A and B are admitted
    allowed_a, _ = limiter.check_and_record(
        "client_a", max_requests=5, window_seconds=60
    )
    allowed_b, _ = limiter.check_and_record(
        "client_b", max_requests=5, window_seconds=60
    )
    assert allowed_a is True
    assert allowed_b is True
    assert len(limiter._buckets) == 2

    # Client C arrives while A and B are active: rejected (fails closed)
    allowed_c, retry_after_c = limiter.check_and_record(
        "client_c", max_requests=5, window_seconds=60
    )
    assert allowed_c is False
    assert retry_after_c == 60

    # Capacity strictly maintained; active buckets not evicted
    assert len(limiter._buckets) == 2
    assert "client_a" in limiter._buckets
    assert "client_b" in limiter._buckets
    assert "client_c" not in limiter._buckets

    # Existing clients continue to operate normally
    allowed_a2, _ = limiter.check_and_record(
        "client_a", max_requests=5, window_seconds=60
    )
    assert allowed_a2 is True

    # Keep Client B active at t = 1030
    clock.advance(30.0)
    limiter.check_and_record("client_b", max_requests=5, window_seconds=60)

    # Advance clock past Client A's window (t = 1065)
    clock.advance(35.0)

    # Now Client C arrives: stale cleanup frees Client A,
    # Client B is preserved, Client C is admitted!
    allowed_c2, _ = limiter.check_and_record(
        "client_c", max_requests=5, window_seconds=60
    )
    assert allowed_c2 is True
    assert len(limiter._buckets) == 2
    assert "client_b" in limiter._buckets
    assert "client_c" in limiter._buckets


def test_rate_limiter_reset() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    limiter.check_and_record("client_1", max_requests=1, window_seconds=60)
    assert not limiter.check_and_record("client_1", max_requests=1, window_seconds=60)[
        0
    ]

    limiter.reset()
    assert limiter.check_and_record("client_1", max_requests=1, window_seconds=60)[0]


def test_rate_limiter_thread_safety() -> None:
    clock = MockClock()
    limiter = SlidingWindowRateLimiter(time_func=clock.time)

    results = []

    def make_request():
        allowed, _ = limiter.check_and_record(
            "concurrent_client", max_requests=50, window_seconds=60
        )
        results.append(allowed)

    threads = [threading.Thread(target=make_request) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly 50 should have succeeded, and 50 should have been rejected
    assert results.count(True) == 50
    assert results.count(False) == 50


def test_get_client_ip_ignores_forwarded_headers() -> None:
    # Scope with directly connected client
    scope = {
        "type": "http",
        "client": ("192.168.1.100", 54321),
        "headers": [
            (b"x-forwarded-for", b"10.0.0.1"),
            (b"x-real-ip", b"10.0.0.2"),
            (b"forwarded", b"for=10.0.0.3"),
        ],
    }

    # Must extract directly connected client address, NOT spoofed headers
    ip = get_client_ip(scope)
    assert ip == "192.168.1.100"


def test_get_client_ip_handles_missing_client() -> None:
    scope = {
        "type": "http",
        "client": None,
        "headers": [],
    }
    ip = get_client_ip(scope)
    assert ip == "unknown"
