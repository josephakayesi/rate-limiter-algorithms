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

def drift(window_size: int = 10, limit: int = 5, gap: float = 1.5) -> None:
    """Send one steady stream to the counter and the log, and mark where they disagree.

    The log is the exact answer, because it counts the requests that really fall inside
    the last `window_size` seconds. The counter only estimates that number, because it
    spreads the previous window's count evenly across that window. No stream is that
    even, not even this one, so the two verdicts drift apart by a request either way.

    `gap` is the pause between requests. The default offers more than `limit` per
    window, so both limiters deny often enough for the drift to show.
    """
    counter = SlidingWindowCounterRateLimiter(window_size, limit)
    log = SlidingWindowLogRateLimiter(window_size, limit)

    def side(limiter: Limiter, allowed: bool) -> str:
        status = 'ALLOW' if allowed else 'DENY '
        return f'[{status}] {limiter.count_for(USER, API)}/{limiter.limit}'

    sent = counter_total = log_total = 0
    print(f'Window: {window_size}s, limit: {limit}, one request every {gap}s\n')

    try:
        while True:
            counter_allowed = counter.is_allowed(USER, API)
            log_allowed = log.is_allowed(USER, API)
            sent += 1
            counter_total += int(counter_allowed)
            log_total += int(log_allowed)

            ts = datetime.now(UTC).strftime('%H:%M:%S')
            note = '  <-- disagree' if counter_allowed != log_allowed else ''
            print(
                f'{ts}  counter {side(counter, counter_allowed)}'
                f'  log {side(log, log_allowed)}{note}'
            )
            time.sleep(gap)
    finally:
        print(f'\n{sent} sent: counter allowed {counter_total}, log allowed {log_total}')

DEMOS = {
    'fwc': lambda: stream(FixedWindowCounterRateLimiter(10, 5), gap=1),
    'swl': lambda: stream(SlidingWindowLogRateLimiter(10, 5)),
    'swc': lambda: stream(SlidingWindowCounterRateLimiter(10, 5)),
    'fwc-burst': lambda: burst(FixedWindowCounterRateLimiter(10, 5)),
    'swc-burst': lambda: burst(SlidingWindowCounterRateLimiter(10, 5)),
    'swc-drift': drift,
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
