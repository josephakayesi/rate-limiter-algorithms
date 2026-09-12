"""Fixed window counter rate limiter.

Time is cut into fixed windows of `window_size` seconds, aligned to the Unix epoch.
Each (api, user, window) pair gets a counter. A request is allowed while that counter
is below `limit`, and every counter resets when the window rolls over.

The tradeoff is the boundary burst: a client can send `limit` requests at the end of
one window and `limit` more at the start of the next, so up to 2 * limit requests land
inside a single `window_size` span. `main.py` demonstrates this.
"""
import time

class FixedWindowCounterRateLimiter:
	"""Args:
	    window_size: length of each window, in seconds.
	    limit: requests allowed per user, per api, per window.
	"""
	def __init__(self, window_size: int, limit: int):
		self.window_size = window_size
		self.limit = limit
		self.cache = {}

	def is_allowed(self, user_id: str, api: str) -> bool:
		window = int(time.time()) // self.window_size
		key = f'ratelimit:{api}:{user_id}:{window}'

		# Drop counters from earlier windows. They can never be read again.
		# This is an O(n) scan on every call, which is fine for a demo. Use a
		# TTL cache (or Redis EXPIRE) once the cache holds many keys.
		for k in [k for k in self.cache if not k.endswith(f':{window}')]:
			del self.cache[k]

		count = self.cache.get(key, 0)

		if count < self.limit:
			self.cache[key] = count + 1
			return True

		return False
