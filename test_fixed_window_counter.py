"""Self-check for the fixed window counter. Run: uv run test_fixed_window_counter.py"""
import time

from algorithms import FixedWindowCounterRateLimiter

API = '/api/login'

# The limit holds inside one window, and the counter is per user.
limiter = FixedWindowCounterRateLimiter(window_size=60, limit=2)
assert [limiter.is_allowed('zara', API) for _ in range(3)] == [True, True, False]
assert limiter.is_allowed('bo', API)

# Crossing a boundary resets the counter and drops the old key.
rollover = FixedWindowCounterRateLimiter(window_size=1, limit=1)
assert rollover.is_allowed('zara', API)
assert not rollover.is_allowed('zara', API)
time.sleep(1.1)
assert rollover.is_allowed('zara', API)
assert len(rollover.cache) == 1
