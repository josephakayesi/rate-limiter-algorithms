"""Self-check for the token bucket. Run: uv run tests/test_token_bucket.py"""
import time

import context  # noqa: F401  the path shim, so `algorithms` resolves
from algorithms import TokenBucketRateLimiter

API = '/api/login'
USER = 'zara'
KEY = f'ratelimit:{API}:{USER}'

def at_second_start() -> None:
    """Sleep to just after the next whole second. The limiter works in whole
    seconds, so a check that starts mid-second is not repeatable."""
    time.sleep(1 - time.time() % 1 + 0.05)

# A full bucket serves a burst of capacity, and then nothing.
at_second_start()
limiter = TokenBucketRateLimiter(capacity=2, refill_rate=0.5)
assert [limiter.is_allowed(USER, API) for _ in range(3)] == [True, True, False]
assert limiter.count_for(USER, API) == 0

# The record is per user, and a user with no record yet holds a full bucket.
assert limiter.count_for('bo', API) == 2
assert limiter.is_allowed('bo', API)
assert len(limiter.cache) == 2

# At 0.5 per second, one second earns half a token, which buys nothing. The
# half is kept rather than rounded away, which is why the next second is enough.
time.sleep(1)
assert limiter.count_for(USER, API) == 0
assert not limiter.is_allowed(USER, API)

time.sleep(1)
# count_for works the drip out for itself, because only is_allowed writes. The
# stored count is still the 0.5 that the denial above left behind.
assert limiter.count_for(USER, API) == 1
assert limiter.cache[KEY]['tokens'] == 0.5
assert limiter.is_allowed(USER, API)

# The denial above moved `last` too. If it had not, the seconds before it would
# be paid for a second time here and this request would be allowed.
time.sleep(1)
assert not limiter.is_allowed(USER, API)
time.sleep(1)
assert limiter.is_allowed(USER, API)

# The bucket never holds more than capacity, however long the drip runs.
at_second_start()
fast = TokenBucketRateLimiter(capacity=2, refill_rate=5)
assert [fast.is_allowed(USER, API) for _ in range(3)] == [True, True, False]
time.sleep(1)
assert fast.count_for(USER, API) == 2
assert [fast.is_allowed(USER, API) for _ in range(3)] == [True, True, False]
