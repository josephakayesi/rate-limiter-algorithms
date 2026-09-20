"""Sliding window log rate limiter.

Each user gets a log of the timestamps of their recent requests. Before a decision,
timestamps older than `window_size` seconds are dropped off the front of the log. A
request is allowed while what remains is shorter than `limit`.

The window moves with the clock rather than snapping to a boundary, so the boundary
burst of the fixed window counter cannot happen. `limit` is enforced over every
`window_size` span, not just over the ones that start on a multiple of the size.

The tradeoff is memory: the log holds one timestamp per allowed request, so a user at
the limit costs `limit` timestamps, where the fixed window counter costs one integer.

Nothing here evicts a user. A log is only trimmed when that same user sends another
request, so a user who goes quiet keeps their timestamps for as long as the process
runs, and the cache grows with every user ever seen. In Redis the same algorithm is a
sorted set per user, and an EXPIRE on that set retires an idle user for free. In this
process it would take a TTL cache or a cap on the number of users.
"""
import time
from collections import defaultdict, deque

class SlidingWindowLogRateLimiter:
	"""Args:
	    window_size: how far back the window reaches, in seconds.
	    limit: requests allowed per user, per api, within that window.
	"""
	def __init__(self, window_size: int, limit: int):
		self.window_size: int = window_size
		self.limit: int = limit
		# One log per user: a deque of epoch seconds, oldest first. Rejected
		# requests are never logged, so the log holds allowed requests only.
		# Entries are never removed. See the note at the top of the file.
		self.cache: defaultdict[str, deque[int]] = defaultdict(deque)

	def is_allowed(self, user_id: str, api: str) -> bool:
		key = f'ratelimit:{api}:{user_id}'
		log = self.cache[key]
		now = int(time.time())

		# Drop the timestamps that have fallen out of the window. The log is in
		# order, so the expired ones are always at the front and the loop stops
		# at the first timestamp that is still inside.
		while log and now - log[0] >= self.window_size:
			_ = log.popleft()

		if len(log) < self.limit:
			log.append(now)
			return True

		return False

	def count_for(self, user_id: str, api: str) -> int:
		"""Requests this user has made so far in the current window."""
		key = f'ratelimit:{api}:{user_id}'
		log = self.cache.get(key)
		now = int(time.time())

		if not log:
			return 0

		# The log is only trimmed inside is_allowed, so it can hold expired
		# timestamps when this is called between requests. Count what is still
		# inside the window rather than trusting the length.
		return sum(1 for ts in log if now - ts < self.window_size)
