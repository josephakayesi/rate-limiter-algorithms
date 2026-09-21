# Rate limiter algorithms

Small, readable implementations of the common rate limiting algorithms, one per folder.
Each one comes with a terminal demo that shows how it behaves and where it breaks.

## Algorithms

- [x] Fixed window counter
- [x] Sliding window log
- [x] Sliding window counter
- [x] Token bucket
- [x] Leaky bucket

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

## Token bucket

Each user gets a bucket of `capacity` tokens under the key `ratelimit:{api}:{user_id}`. A
request spends one token, and a request that finds an empty bucket is denied. Tokens drip
back in at `refill_rate` per second, and the bucket never holds more than `capacity`.
Nothing adds tokens on a schedule. The limiter credits `elapsed * refill_rate` tokens on
the next request and caps the result, so there is no timer and no background job. A user
costs two numbers, the token count and the second it was last credited.

The two knobs are independent, and none of the window algorithms separate them.
`capacity` is the largest burst a user can send at once. `refill_rate` is the rate they
sustain after that burst. Five requests per 10 seconds, with a burst of five, is
`capacity=5` and `refill_rate=0.5`. Nothing resets, so there is no boundary to stack
requests around. A user recovers one token every `1 / refill_rate` seconds instead of in
jumps.

Tokens are fractional on purpose. At a rate below one per second, a call earns less than
a whole token. Rounding that credit down discards the remainder every time, so a slow
bucket never fills. The fraction stays in the stored count. Only `count_for` rounds, and
only for display, so a bucket holding 0.9 tokens reports 0 rather than a token that is
not there.

The weakness is the burst that `capacity` buys. A user who stayed quiet arrives with a
full bucket, so `capacity` requests can land at once, whatever the sustained rate says.
Over any span of `T` seconds the most a user can send is `capacity + refill_rate * T`.
Size `capacity` for the spike you can absorb, not for the average you want. The limiter
also evicts nobody, so a user who goes quiet keeps their record until the process ends.

## Leaky bucket

Each user gets one record under the key `ratelimit:{api}:{user_id}`, holding the level of
their bucket in requests and the moment that bucket was last leaked. Requests pile up in
the bucket, and the bucket leaks `leak_rate` requests per second. A request is allowed
while the level is below `capacity`, and it then raises the level by one.

Nothing leaks on a schedule. The next request works out how much has leaked since
`last_leak` and takes that off the level. The drain therefore costs nothing between
requests. Only whole requests leak, because half a request cannot leave the bucket.

That rounding is where the care goes. `last_leak` moves forward by the time the leaked
requests took to leave, which is `leaked / leak_rate`, and not to `now`. Moving it to
`now` discards the part of the next request that has already leaked. It does so on every
request, and the bucket then drains slower than `leak_rate` says. The level is also
floored at 0, so an empty bucket banks nothing while it waits.

A queue of request timestamps is the usual drawing of this algorithm. The timestamps
decide nothing though, because only their number is ever read, so two numbers do the
same work and cost less.

What remains is the token bucket seen from the other side, under the substitution
`level == capacity - tokens`. The one behaviour left between them is the grain, because
tokens accrue as fractions and glide, where this leaks whole requests and steps. The
weakness is the same too. A user who stayed quiet arrives to an empty bucket and can
fill it at once. The limiter also evicts nobody, so a quiet user keeps their record
until the process ends.

## Run the demos

```
uv run main.py <demo>
```

The demos are `fwc`, `swl`, `swc`, `tb` and `lb`, plus `fwc-burst`, `swc-burst` and
`swc-drift`. Run `uv run main.py -h` for the list.

`fwc`, `swl` and `swc` are continuous views. Each sends requests until you stop it and
prints a bar of the current count. The fixed window bar empties all at once. The sliding
window bars refill a piece at a time.

`tb` is the same view of a bucket of 5 tokens that refills at 0.5 per second, one request
every second. The bar runs the other way here, because `count_for` reports the tokens
left rather than the requests used. The opening requests drain the bucket, and after that
the bar stays empty and the verdict alternates, which is one token every 2 seconds.

`lb` sends one request per second to a bucket of 5 that leaks at 0.5 per second. Arrivals
beat the leak two to one, so the bar climbs a step every other request. Once the bucket
is full the verdict alternates, which is the leak rate of one request every 2 seconds.

`fwc-burst` and `swc-burst` are the same script against two limiters. Each lines up 1
second before a window boundary, fires a full allowance, crosses the boundary, then fires
a full allowance again. The fixed window counter allows all 10 requests inside about a
second, which is the boundary burst. The sliding window counter denies the second batch.

`swc-drift` sends one stream to the sliding window counter and the sliding window log at
once. It marks every request the two decide differently. The log is the exact
answer, because it counts the requests that are really inside the last `window_size`
seconds. The counter only estimates that number, because it spreads the previous
window's count evenly across that window.

The stream is an ordinary one. It sends a request every 1.5 seconds, which offers about
6.7 requests per window against a limit of 5. Both limiters therefore deny often enough
for the drift to show. There is no burst and no lining up with a boundary. Over a 45
second run, about a third of the requests land on a different verdict. The two running
totals end a request or two apart.

An even stream still drifts, because the requests the counter keeps are not the ones you
send. Each limiter allows a run of requests and then denies for a while. The allowed
requests inside a window therefore sit in a clump, not evenly across it. The estimate
assumes the even spread, so it reads that clump as too many requests or too few. Which
way it goes depends on the half of the window the clump sits in.

The error is bounded by the previous window's count. It also shrinks as the current
window fills, because the previous count carries less weight as `elapsed` grows.

To add a demo, add one entry to the `DEMOS` dict in `main.py`. A limiter needs
`is_allowed`, `count_for` and a `limit` attribute, and `burst` needs `window_size` too.

## Run the checks

```
uv run tests/test_fixed_window_counter.py
uv run tests/test_sliding_window_log.py
uv run tests/test_sliding_window_counter.py
uv run tests/test_token_bucket.py
uv run tests/test_leaky_bucket.py
```

A check passes with no output. It fails with an `AssertionError`. Every check sleeps
through real time, because the limiters work in whole seconds, so each one takes a few
seconds.

Each check imports `tests/context.py` before anything of its own. That module puts the
project root on the path, because Python gives a script only its own folder, which here
is `tests`. Without it, `from algorithms import ...` has nowhere to look.

## Note on state

Every limiter here keeps its state in a plain dict inside the process. Each worker therefore
counts on its own, and a restart forgets everything.

For real traffic across more than one process, move the state to Redis. Read and write have
to happen as one step, or two workers read the same count and both allow a request that the
limit forbids. The fixed window counter needs a Lua script or a `MULTI` block, because the
count and the window number are read, reset, and written together. The sliding window
log maps onto a sorted set per user, where `ZREMRANGEBYSCORE` trims the log and `EXPIRE`
retires a user who goes quiet. The token bucket maps onto a hash per user holding the same
two fields, written by a script for the same reason. An `EXPIRE` of `capacity /
refill_rate` seconds retires an idle user there for free. A bucket with time to fill is
worth the same as no record at all. The leaky bucket is the same shape
as the token bucket, a hash per user under the same script and the same kind of expiry.
