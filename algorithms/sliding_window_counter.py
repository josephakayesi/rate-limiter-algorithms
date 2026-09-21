import time


class SlidingWindowCounterRateLimiter:
    """Args:
    window_size: how far back the window reaches, in seconds.
    limit: requests allowed per user, per api, within that window.
    """

    def __init__(self, window_size: int, limit: int):
        self.window_size: int = window_size
        self.limit: int = limit
        # One record per user: {'window': int, 'count': int, 'prev_count': int}.
        # A new window rolls the record rather than adding to it, so each user
        # holds exactly one record and there is nothing to expire or sweep.
        self.cache: dict[str, dict[str, int]] = {}

    def is_allowed(self, user_id: str, api: str) -> bool:
        key = f"ratelimit:{api}:{user_id}"
        now = int(time.time())
        window = now // self.window_size

        log = self.cache.get(key, {"window": window, "prev_count": 0, "count": 0})
        self.cache[key] = log

        # Roll the record forward before the decision, so the estimate reads the
        # counts of the window that `elapsed` belongs to. A denied request rolls
        # too, which is why this sits above the return below.
        if window - log["window"] == 1:
            log["prev_count"] = log["count"]
            log["count"] = 0
            log["window"] = window
        elif window != log["window"]:
            # Two or more windows of silence, so the window before this one is
            # empty and has nothing to contribute.
            log["prev_count"] = 0
            log["count"] = 0
            log["window"] = window

        elapsed = now % self.window_size
        estimate = log["prev_count"] * (1 - elapsed / self.window_size) + log["count"]

        if estimate >= self.limit:
            return False

        log["count"] += 1
        return True

    def count_for(self, user_id: str, api: str) -> int:
        """The limiter's estimate for this user, over the window ending now.

        This is the number is_allowed decides on, floored to whole requests. It
        is an estimate and not a tally, because the previous window's count is
        spread evenly across that window.
        """
        log = self.cache.get(f"ratelimit:{api}:{user_id}")
        now = int(time.time())

        if log is None:
            return 0

        # The record is only rolled inside is_allowed, so it can be one or more
        # windows behind when this is called between requests. Roll it here as
        # arithmetic rather than trusting the counts as they stand.
        gap = now // self.window_size - log["window"]

        if gap == 0:
            prev_count, count = log["prev_count"], log["count"]
        elif gap == 1:
            prev_count, count = log["count"], 0
        else:
            return 0

        elapsed = now % self.window_size
        return int(prev_count * (1 - elapsed / self.window_size) + count)
