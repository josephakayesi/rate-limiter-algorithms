"""Self-check for the sliding window log. Run: uv run test_sliding_window_log.py"""
import time

from algorithms import SlidingWindowLogRateLimiter

API = '/api/login'

# The limit holds inside one window, and the log is per user.
limiter = SlidingWindowLogRateLimiter(window_size=60, limit=2)
assert [limiter.is_allowed('zara', API) for _ in range(3)] == [True, True, False]
assert limiter.is_allowed('bo', API)
assert limiter.count_for('zara', API) == 2
assert limiter.count_for('bo', API) == 1

# Timestamps are whole seconds, so start just after a second boundary.
time.sleep(1 - time.time() % 1)

# The window slides. One slot frees up as the oldest request ages out, rather
# than the whole count resetting the way the fixed window counter does.
sliding = SlidingWindowLogRateLimiter(window_size=2, limit=2)
assert sliding.is_allowed('zara', API)
time.sleep(1)
assert sliding.is_allowed('zara', API)
assert not sliding.is_allowed('zara', API)
time.sleep(1.2)
assert sliding.is_allowed('zara', API)
assert sliding.count_for('zara', API) == 2

# count_for does not trust the length, because only is_allowed trims the log.
time.sleep(2.1)
assert sliding.count_for('zara', API) == 0
assert len(sliding.cache[f'ratelimit:{API}:zara']) == 2
