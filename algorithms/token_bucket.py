"""Token bucket rate limiter.

Each user gets a bucket of `capacity` tokens, held under the key
`ratelimit:{api}:{user_id}`. A request spends one token, and tokens drip back in at
`refill_rate` per second. The bucket never holds more than `capacity`.

The drip is what separates this from the window algorithms. Nothing resets, so there is
no boundary to stack requests around, and a user recovers at a steady rate rather than
in jumps. `capacity` and `refill_rate` are independent: the first is the largest burst a
user can send, the second is the rate they sustain once the bucket is empty. Five
requests per 10 seconds, burst of five, is `capacity=5` and `refill_rate=0.5`.

Tokens are fractional on purpose. At a rate below one per second a call earns less than
a whole token, and rounding that credit down would throw the remainder away every time,
so a slow bucket would never fill. The fraction lives in the stored count. Only
`count_for` rounds, and only for display.

Nothing here evicts a user, so a user who goes quiet keeps their record for as long as
the process runs. In Redis this is a hash per user with the same two fields, written by
a Lua script so the read and the write are one step. An EXPIRE of `capacity /
refill_rate` seconds retires an idle user for free, because a bucket that has had time
to fill is worth the same as no record at all.
"""
import time

class TokenBucketRateLimiter:
	"""Args:
	    capacity: tokens the bucket holds, which is the largest burst allowed.
	    refill_rate: tokens added per second. Rates below 1 are fine.
	"""
	def __init__(self, capacity: int, refill_rate: float):
		self.capacity: int = capacity
		self.refill_rate: float = refill_rate
		# One record per user: {'tokens': float, 'last': the second it was last
		# credited}. Tokens are fractional, so a slow drip is not lost to rounding.
		self.cache: dict[str, dict[str, float]] = {}

	@property
	def limit(self) -> int:
		"""The most this user can send at once, which is the whole bucket.

		The demos scale their bar to `limit`, and every other limiter here has one.
		"""
		return self.capacity

	def is_allowed(self, user_id: str, api: str) -> bool:
		key = f'ratelimit:{api}:{user_id}'
		now = int(time.time())

		log = self.cache.get(key, {'tokens': float(self.capacity), 'last': now})
		self.cache[key] = log

		# Credit the drip since the last decision, then cap. `last` moves whether or
		# not the request is allowed, because the credit is already in the bucket, and
		# leaving `last` behind would pay for those same seconds again on the next call.
		earned = (now - log['last']) * self.refill_rate
		log['tokens'] = min(self.capacity, log['tokens'] + earned)
		log['last'] = now

		# Part of a token buys nothing. What is left stays for the next call.
		if log['tokens'] < 1:
			return False

		log['tokens'] -= 1
		return True

	def count_for(self, user_id: str, api: str) -> int:
		"""Whole tokens this user holds now.

		Only `is_allowed` writes, so the stored count can be several seconds stale when
		this is called between requests. Credit the drip here as arithmetic instead,
		and round down: a bucket holding 0.9 tokens cannot serve a request, so it
		reports 0 rather than a token that is not there.
		"""
		log = self.cache.get(f'ratelimit:{api}:{user_id}')

		if log is None:
			return self.capacity

		earned = (int(time.time()) - log['last']) * self.refill_rate
		return int(min(self.capacity, log['tokens'] + earned))
