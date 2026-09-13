import random
import time
from datetime import datetime, timezone
from algorithms import FixedWindowCounterRateLimiter, SlidingWindowLogRateLimiter

def run_burst_demo():
    window_size = 10
    limit = 5
    limiter = FixedWindowCounterRateLimiter(window_size=window_size, limit=limit)
    user_id = 'zara'
    api = '/api/login'

    print(f"Window: {window_size}s, Limit: {limit}\n")

    # Wait until 6s into the current window (4s left before boundary)
    now = time.time()
    offset = now % window_size
    sleep_to_target = (6 - offset) % window_size
    print(f"Waiting {sleep_to_target:.1f}s until 6s into window...\n")
    time.sleep(sleep_to_target)

    print("--- Firing 5 requests (window N) ---\n")
    for i in range(limit):
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
        allowed = limiter.is_allowed(user_id=user_id, api=api)
        window = int(time.time()) // window_size
        count = limiter.count_for(user_id=user_id, api=api)
        bar = '█' * count + '░' * (limit - count)
        status = 'ALLOW' if allowed else 'DENY '
        print(f'{ts}  [{status}]  [{bar}]  {count}/{limit}  window={window}')
        time.sleep(1)

    # Wait for boundary to cross
    time.sleep(1)
    print(f"\n{'─' * 50}")
    print(f"  Window boundary crossed")
    print(f"{'─' * 50}\n")

    print("--- Firing 5 more requests (window N+1) ---\n")
    for i in range(limit):
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
        allowed = limiter.is_allowed(user_id=user_id, api=api)
        window = int(time.time()) // window_size
        count = limiter.count_for(user_id=user_id, api=api)
        bar = '█' * count + '░' * (limit - count)
        status = 'ALLOW' if allowed else 'DENY '
        print(f'{ts}  [{status}]  [{bar}]  {count}/{limit}  window={window}')
        time.sleep(1)

    print(f"\nTotal: {limit * 2} requests allowed, all 'legal' per window")
    print(f"But concentrated in ~{window_size}s around the boundary")


def run_fwc():
    limiter = FixedWindowCounterRateLimiter(window_size=10, limit=5)

    user_id = 'zara'
    api = '/api/login'


    while True:
    # for _ in range(20):
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
        allowed = limiter.is_allowed(user_id=user_id, api=api)
        count = limiter.count_for(user_id=user_id, api=api)

        bar = '█' * count + '░' * (limiter.limit - count)
        status = 'ALLOW' if allowed else 'DENY '
        print(f'{ts}  [{status}]  [{bar}]  {count}/{limiter.limit}')
        time.sleep(1)

def run_swl():
    limiter = SlidingWindowLogRateLimiter(window_size=10, limit=5)

    user_id = 'zara'
    api = '/api/login'


    while True:
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
        allowed = limiter.is_allowed(user_id=user_id, api=api)
        count = limiter.count_for(user_id=user_id, api=api)

        bar = '█' * count + '░' * (limiter.limit - count)
        status = 'ALLOW' if allowed else 'DENY '
        # Uneven gaps, so the log ages out one timestamp at a time instead of
        # in lockstep with the requests.
        gap = random.uniform(1, 5)
        print(f'{ts}  [{status}]  [{bar}]  {count}/{limiter.limit}  next in {gap:.1f}s')
        time.sleep(gap)

def main():
    # Fixed window
    # run_fwc()
    # run_burst_demo()

    # Sliding window log
    run_swl()



if __name__ == "__main__":
    main()
