"""Self-check for the sliding window counter. Run: uv run tests/test_sliding_window_counter.py"""
import time

import context  # noqa: F401  the path shim, so `algorithms` resolves
from algorithms import SlidingWindowCounterRateLimiter

API = '/api/login'

def at_window_start(window_size: int) -> None:
    """Sleep to just after the start of the next window. The limiter works in
    whole seconds, so a check that starts mid-second is not repeatable."""
    time.sleep(window_size - time.time() % window_size + 0.05)

# The limit holds inside one window, and the record is per user.
limiter = SlidingWindowCounterRateLimiter(window_size=60, limit=2)
assert [limiter.is_allowed('zara', API) for _ in range(3)] == [True, True, False]
assert limiter.is_allowed('bo', API)
assert limiter.count_for('zara', API) == 2
assert limiter.count_for('bo', API) == 1

# Crossing a boundary carries the previous window's count over, weighted by how
# much of the window is left. At the start of the new window none of it has aged
# out, so the request is still denied where the fixed window counter allows it.
at_window_start(2)
carry = SlidingWindowCounterRateLimiter(window_size=2, limit=4)
assert [carry.is_allowed('zara', API) for _ in range(5)] == [True, True, True, True, False]
at_window_start(2)
assert carry.count_for('zara', API) == 4
assert not carry.is_allowed('zara', API)

# Halfway through the new window, half of the carried count has aged out and two
# slots are back. The allowance returns a piece at a time, not all at once.
time.sleep(1)
assert carry.count_for('zara', API) == 2
assert [carry.is_allowed('zara', API) for _ in range(3)] == [True, True, False]

# Two whole windows of silence leave nothing to carry. The stored count is still
# 2, because only is_allowed writes, so count_for works the roll out for itself
# rather than trusting the counts as they stand.
time.sleep(4)
assert carry.count_for('zara', API) == 0
assert carry.cache[f'ratelimit:{API}:zara']['count'] == 2

# Recovery is complete, and the user still costs one record.
assert carry.is_allowed('zara', API)
assert len(carry.cache) == 1
