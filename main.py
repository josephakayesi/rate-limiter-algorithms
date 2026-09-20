"""Terminal demos for the rate limiters. Run: uv run main.py <demo>

`Limiter` and `WindowedLimiter` below are the whole contract a limiter needs to be
demo-ready. A bucket algorithm, which has no windows, satisfies `Limiter` alone and so
gets a `stream` entry and no `burst` one.
"""
import argparse
import random
import time
from datetime import UTC, datetime
from typing import Protocol, cast

from algorithms import (
    FixedWindowCounterRateLimiter,
    SlidingWindowCounterRateLimiter,
    SlidingWindowLogRateLimiter,
)

USER = 'zara'
API = '/api/login'

class Limiter(Protocol):
    limit: int

    def is_allowed(self, user_id: str, api: str) -> bool: ...
    def count_for(self, user_id: str, api: str) -> int: ...

class WindowedLimiter(Limiter, Protocol):
    window_size: int

def show(limiter: Limiter, allowed: bool, note: str = '') -> None:
    """Print one decision: the time, the verdict, a bar of the current count."""
    count = limiter.count_for(USER, API)
    # The sliding window counter can estimate above the limit, so clamp the bar.
    filled = min(count, limiter.limit)
    bar = '█' * filled + '░' * (limiter.limit - filled)
    ts = datetime.now(UTC).strftime('%H:%M:%S')
    status = 'ALLOW' if allowed else 'DENY '
    print(f'{ts}  [{status}]  [{bar}]  {count}/{limiter.limit}  {note}'.rstrip())

def stream(limiter: Limiter, gap: float | None = None) -> None:
    """Send requests until you stop it, printing the count after each one.

    `gap` is the pause between requests, in seconds. None spaces them unevenly, so
    the window ages out between requests instead of in lockstep with them.
    """
    while True:
        allowed = limiter.is_allowed(USER, API)
        pause = random.uniform(1, 5) if gap is None else gap
        show(limiter, allowed, f'next in {pause:.1f}s')
        time.sleep(pause)

def burst(limiter: WindowedLimiter) -> None:
    """Fire a full allowance just before a window boundary, then again just after.

    The fixed window counter allows both batches, so 2 * limit requests land inside
    about a second. The sliding window counter carries the first batch into the new
    window and denies the second.
    """
    size, limit = limiter.window_size, limiter.limit
    print(f'Window: {size}s, limit: {limit}\n')

    # Line up 1 second before the next boundary, with the whole batch to follow
    # back to back, so every request of it lands inside the same window.
    time.sleep((size - 1 - time.time() % size) % size)

    print(f'--- {limit} requests, 1s before the boundary ---\n')
    for _ in range(limit):
        show(limiter, limiter.is_allowed(USER, API))

    time.sleep(1.1)
    print(f'\n{"─" * 46}\n  boundary crossed\n{"─" * 46}\n')

    print(f'--- {limit} more requests, just after ---\n')
    for _ in range(limit):
        show(limiter, limiter.is_allowed(USER, API))

DEMOS = {
    'fwc': lambda: stream(FixedWindowCounterRateLimiter(10, 5), gap=1),
    'swl': lambda: stream(SlidingWindowLogRateLimiter(10, 5)),
    'swc': lambda: stream(SlidingWindowCounterRateLimiter(10, 5)),
    'fwc-burst': lambda: burst(FixedWindowCounterRateLimiter(10, 5)),
    'swc-burst': lambda: burst(SlidingWindowCounterRateLimiter(10, 5)),
}

def main() -> None:
    parser = argparse.ArgumentParser(description='Rate limiter demos.')
    _ = parser.add_argument('demo', choices=DEMOS, help='which demo to run')
    try:
        DEMOS[cast(str, parser.parse_args().demo)]()
    except KeyboardInterrupt:
        print()

if __name__ == '__main__':
    main()
