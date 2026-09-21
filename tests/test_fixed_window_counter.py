"""Self-check for the fixed window counter. Run: uv run tests/test_fixed_window_counter.py"""
import time

import context  # noqa: F401  the path shim, so `algorithms` resolves
from algorithms import FixedWindowCounterRateLimiter

API = '/api/login'

# The limit holds inside one window, and the count is per user.
limiter = FixedWindowCounterRateLimiter(window_size=60, limit=2)
assert [limiter.is_allowed('zara', API) for _ in range(3)] == [True, True, False]
assert limiter.is_allowed('bo', API)
assert limiter.count_for('zara', API) == 2
assert limiter.count_for('bo', API) == 1

# Crossing a boundary resets the record in place, rather than adding a second one.
rollover = FixedWindowCounterRateLimiter(window_size=1, limit=1)
assert rollover.is_allowed('zara', API)
assert not rollover.is_allowed('zara', API)
time.sleep(1.1)
assert rollover.count_for('zara', API) == 0
assert rollover.is_allowed('zara', API)
assert len(rollover.cache) == 1
