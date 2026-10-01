from app.services.rate_limiter import TokenBucketRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_first_calls_up_to_capacity_do_not_sleep():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(5, time_fn=clock.time, sleep_fn=clock.sleep)

    for _ in range(5):
        limiter.acquire("zerodha")

    assert clock.sleeps == []


def test_exceeding_capacity_sleeps_for_the_right_duration():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(2, time_fn=clock.time, sleep_fn=clock.sleep)

    limiter.acquire("zerodha")
    limiter.acquire("zerodha")
    limiter.acquire("zerodha")  # bucket empty -- must wait 1/rate = 0.5s

    assert clock.sleeps == [0.5]


def test_separate_brokers_have_independent_buckets():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(1, time_fn=clock.time, sleep_fn=clock.sleep)

    limiter.acquire("zerodha")
    limiter.acquire("upstox")  # different key -- its own full bucket, no sleep

    assert clock.sleeps == []


def test_tokens_refill_over_time():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(1, time_fn=clock.time, sleep_fn=clock.sleep)

    limiter.acquire("zerodha")  # bucket now empty
    clock.now += 1.0  # a full second passes -- one token regenerates
    limiter.acquire("zerodha")  # should not need to sleep

    assert clock.sleeps == []
