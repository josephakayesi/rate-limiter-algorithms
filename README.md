# Rate limiter algorithms

Small, readable implementations of the common rate limiting algorithms, one per folder,
each with a terminal demo that shows how it behaves and where it breaks.

## Algorithms

- [x] Fixed window counter
- [ ] Sliding window log
- [ ] Sliding window counter
- [ ] Token bucket
- [ ] Leaky bucket

## Fixed window counter

Time is cut into fixed windows of `window_size` seconds, aligned to the Unix epoch. The
window number for a request is `int(time.time()) // window_size`. Each user, api, and window
gets its own counter under the key `ratelimit:{api}:{user_id}:{window}`. A request is allowed
while that counter is below `limit`. When the window number changes, the key changes too, so
every counter starts again from zero.

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

The limiter keeps its counters in a plain dict inside the process. Each worker therefore
counts on its own, and a restart forgets everything. For real traffic across more than one
process, hold the counters in Redis and let `EXPIRE` remove the old windows.
