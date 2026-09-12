# Rate limiter algorithms

Small, readable implementations of the common rate limiting algorithms, one per folder.
Each one comes with a terminal demo that shows how it behaves and where it breaks.

## Algorithms

- [x] Fixed window counter
- [ ] Sliding window log
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

## Run the demos

```
uv run main.py
```

This operates `run_burst_demo()`. It waits until 6 seconds into the current window, fires 5
requests, crosses the boundary, then fires 5 more. All 10 are allowed, inside about 10
seconds.

`main.py` also has `run_fwc()`, a continuous view that sends one request per second and
prints a bar of the current count. To use it instead, swap the commented lines in `main()`.

## Run the check

```
uv run test_fixed_window_counter.py
```

The check passes with no output. It fails with an `AssertionError`.

## Note on state

The limiter keeps its records in a plain dict inside the process. Each worker therefore
counts on its own, and a restart forgets everything. The dict grows with the number of
users and never with uptime.

For real traffic across more than one process, move the records to Redis. Reading the
record, resetting it, and incrementing it have to happen as one step, so use a Lua script
or a `MULTI` block. Otherwise two workers read the same count, and both allow a request that
the limit forbids.
