"""Self-check for the leaky bucket. Run: uv run test_leaky_bucket.py"""
import time

from algorithms import LeakyBucketRateLimiter

API = '/api/login'
USER = 'zara'
KEY = f'ratelimit:{API}:{USER}'

# The bucket holds capacity, and the record is per user.
limiter = LeakyBucketRateLimiter(capacity=3, leak_rate=2.0)
assert [limiter.is_allowed(USER, API) for _ in range(4)] == [True, True, True, False]
assert limiter.count_for(USER, API) == 3
assert limiter.limit == 3
assert limiter.is_allowed('bo', API)
assert limiter.count_for('bo', API) == 1
assert len(limiter.cache) == 2

# Only whole requests leak. Three quarters of a second at 2 per second leaks one
# request, and count_for works that out rather than trusting the length.
time.sleep(0.75)
assert limiter.count_for(USER, API) == 2
assert limiter.cache[KEY]['level'] == 3

# The leak reaches the level on the next request, which frees real room.
assert limiter.is_allowed(USER, API)
assert limiter.cache[KEY]['level'] == 3

# That request leaked 0.75 seconds of bucket but only one whole request, so last_leak
# moved by 0.5 and a quarter second of leak is still owed. A further 0.25 therefore
# completes a second leak. Advancing last_leak to now instead would drop that quarter
# second and leave the count at 3, draining slower than leak_rate says.
time.sleep(0.25)
assert limiter.count_for(USER, API) == 2

# An empty bucket banks nothing while it waits. A second of leak on an empty bucket
# does not buy a fourth slot in the burst that follows.
idle = LeakyBucketRateLimiter(capacity=3, leak_rate=2.0)
assert idle.is_allowed(USER, API)
time.sleep(1.0)
assert idle.count_for(USER, API) == 0
assert [idle.is_allowed(USER, API) for _ in range(4)] == [True, True, True, False]

# A denied request does not raise the level, so a flood does not add to the bucket it
# failed to join.
assert idle.cache[KEY]['level'] == 3
assert not idle.is_allowed(USER, API)
assert idle.cache[KEY]['level'] == 3
