# Rate limiter algorithms

Small, readable implementations of the common rate limiting algorithms, one per folder.
Each one comes with a terminal demo that shows how it behaves and where it breaks.

## Algorithms

- [x] Fixed window counter
- [x] Sliding window log
- [ ] Sliding window counter
- [ ] Token bucket
- [ ] Leaky bucket

## Fixed window counter

Time is cut into fixed windows of `window_size` seconds, aligned to the Unix epoch. The
window number for a request is `int(time.time()) // window_size`. Each user gets one record
under the key `ratelimit:{api}:{user_id}`, holding a count and the window number that count
belongs to. A request is allowed while the count is below `limit`.

A window never has to be closed. On the first request of a new window, the stored window
number no longer matches the current one. The record is then overwritten with a count of
one. Each user therefore holds exactly one record, whatever the uptime, and there is
nothing to expire or sweep.

The weakness is the boundary burst. A client can send `limit` requests at the end of one
window and `limit` more at the start of the next. Both windows are inside their limit, but
`2 * limit` requests land in a span shorter than `window_size`. The demo is built to show
exactly this.

## Sliding window log

Each user gets a log of the timestamps of their allowed requests, held in a deque under
the key `ratelimit:{api}:{user_id}`. Before each decision, the limiter drops the
timestamps that are `window_size` seconds old or older. They sit at the front of the log,
so the trim stops at the first timestamp that is still inside. A request is allowed while
what remains is shorter than `limit`.

This is what the fixed window counter cannot do. The window ends `window_size` seconds
before now, whenever now happens to be, so `limit` holds over every span of that length.
There is no boundary to stack requests around. A user at the limit recovers one slot at a
time, as their oldest request ages out. The whole allowance never comes back at once.

The weakness is memory. The log holds one timestamp per allowed request. A user at the
limit therefore costs `limit` timestamps, where the fixed window counter costs one
integer. The limiter also evicts nobody, so a user who goes quiet keeps their log until
the process ends.

## Run the demos

```
uv run main.py
```

`main()` calls one runner at a time, and the others sit commented out. Uncomment the one
you want.

`run_burst_demo()` waits until 6 seconds into the current window, fires 5 requests, crosses
the boundary, then fires 5 more. All 10 are allowed, inside about 10 seconds, which is the
boundary burst.

`run_fwc()` and `run_swl()` are continuous views. Each sends one request per second and
prints a bar of the current count. The fixed window bar empties all at once. The sliding
window bar refills one slot at a time.

## Run the checks

```
uv run test_fixed_window_counter.py
uv run test_sliding_window_log.py
```

A check passes with no output. It fails with an `AssertionError`. The sliding window log
check sleeps through several windows, so it takes a few seconds.

## Note on state

Both limiters keep their state in a plain dict inside the process. Each worker therefore
counts on its own, and a restart forgets everything.

For real traffic across more than one process, move the state to Redis. Read and write have
to happen as one step, or two workers read the same count and both allow a request that the
limit forbids. The fixed window counter needs a Lua script or a `MULTI` block, because the
count and the window number are read, reset, and written together. The sliding window
log maps onto a sorted set per user, where `ZREMRANGEBYSCORE` trims the log and `EXPIRE`
retires a user who goes quiet.
