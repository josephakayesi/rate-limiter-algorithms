"""Fixed window counter rate limiter.

Time is cut into fixed windows of `window_size` seconds, aligned to the Unix epoch.
Each user gets one record, holding a count and the number of the window that count
belongs to. A request is allowed while the count is below `limit`. When the window
number changes, the record is reset in place and counting starts again from one.

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
		self.window_size: int = window_size
		self.limit: int = limit
		# One record per user: {'count': int, 'window': int}. A new window
		# overwrites the record, so no old windows are left to clean up.
		self.cache: dict[str, dict[str, int]] = {}

	def is_allowed(self, user_id: str, api: str) -> bool:
		window = int(time.time()) // self.window_size
		key = f'ratelimit:{api}:{user_id}'
		record = self.cache.get(key)

		# A new user, or a window that has ended. Both start a fresh window at 1.
		if record is None or record['window'] != window:
			self.cache[key] = {'count': 1, 'window': window}
			return True

		if record['count'] < self.limit:
			record['count'] += 1
			return True

		return False

	def count_for(self, user_id: str, api: str) -> int:
		"""Requests this user has made so far in the current window."""
		record = self.cache.get(f'ratelimit:{api}:{user_id}')

		if record is None or record['window'] != int(time.time()) // self.window_size:
			return 0

		return record['count']
