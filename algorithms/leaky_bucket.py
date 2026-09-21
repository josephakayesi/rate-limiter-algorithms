"""Leaky bucket rate limiter.

Each user gets one record under the key `ratelimit:{api}:{user_id}`, holding the level of
their bucket in requests and the moment that bucket was last leaked. A request raises the
level by one, and the bucket leaks `leak_rate` requests per second. A request is allowed
while the level is below `capacity`.

Nothing leaks on a schedule. The next request works out how much has leaked since
`last_leak` and takes that off the level, so the drain costs nothing between requests.
Only whole requests leak, because half a request cannot leave the bucket.

That rounding is where the care goes. `last_leak` moves forward by the time the leaked
requests took to leave, which is `leaked / leak_rate`, and not to `now`. Moving it to
`now` discards the part of the next request that has already leaked. It does so on every
request, and the bucket then drains slower than `leak_rate` says. The level is also
floored at 0, so an empty bucket banks nothing while it waits.

This is the token bucket seen from the other side, under the substitution
`level == capacity - tokens`. The one behaviour left between them is the grain: tokens
accrue as fractions and glide, where this leaks whole requests and steps. A queue of
timestamps is the usual drawing of this algorithm, but the timestamps decide nothing, so
two numbers do the same work.

Nothing here evicts a user, so a user who goes quiet keeps their record until the process
ends. In Redis this is a hash per user with the same two fields, written by a Lua script
so the read and the write are one step, and an `EXPIRE` of `capacity / leak_rate` seconds
retires an idle user for free, because a bucket with time to empty is worth the same as
no record.
"""
import time

class LeakyBucketRateLimiter:
	"""Args:
	    capacity: requests the bucket holds, which is the largest burst allowed.
	    leak_rate: requests leaving the bucket per second.
	"""
	def __init__(self, capacity: int, leak_rate: float):
		self.capacity: int = capacity
		self.leak_rate: float = leak_rate
		# One record per user: {'level': requests in the bucket, 'last_leak': the
		# moment it last leaked}. A user with no record yet leaks from now.
		self.cache: dict[str, dict[str, float]] = {}

	@property
	def limit(self) -> int:
		"""The most this user can have in the bucket, which is the whole bucket.

		The demos scale their bar to `limit`, and every other limiter here has one.
		"""
		return self.capacity

	def is_allowed(self, user_id: str, api: str) -> bool:
		key = f'ratelimit:{api}:{user_id}'
		now = time.time()

		log = self.cache.get(key, {'level': 0.0, 'last_leak': now})
		self.cache[key] = log

		# Take off what has leaked since last time, and floor the level at 0, so leak
		# an empty bucket had no use for is gone rather than banked.
		leaked = int((now - log['last_leak']) * self.leak_rate)
		log['level'] = max(0.0, log['level'] - leaked)

		# Move `last_leak` by what leaked and not to `now`, so the part of a request
		# that has not leaked yet is still there next time.
		log['last_leak'] += leaked / self.leak_rate

		if log['level'] < self.capacity:
			log['level'] += 1
			return True

		return False

	def count_for(self, user_id: str, api: str) -> int:
		"""Requests this user has in the bucket now.

		Only `is_allowed` leaks, so the stored level can be several requests out of
		date when this is called between requests. Work the leak out here as
		arithmetic rather than trusting the level as it stands.
		"""
		log = self.cache.get(f'ratelimit:{api}:{user_id}')

		if log is None:
			return 0

		leaked = int((time.time() - log['last_leak']) * self.leak_rate)
		return int(max(0.0, log['level'] - leaked))
