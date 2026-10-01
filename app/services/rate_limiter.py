import threading
import time
from typing import Callable

from app.config import settings


class TokenBucketRateLimiter:
    """
    One token bucket per key (broker name), so calling Zerodha a lot never
    throttles calls to Upstox. `acquire()` blocks (sleeps) just long enough
    to stay under `rate_per_second`, rather than failing outright --
    proactive throttling to avoid *triggering* a real broker's rate limit
    in the first place, which complements (not replaces) the reactive
    retry-on-429 handling in app/services/retry.py.

    `time_fn`/`sleep_fn` are injectable so tests can run with a fake clock
    instead of real wall-clock delays.
    """

    def __init__(
        self,
        rate_per_second: float,
        *,
        burst: int | None = None,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self.rate = rate_per_second
        self.capacity = burst or max(1, int(rate_per_second))
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._lock = threading.Lock()
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}

    def acquire(self, key: str) -> None:
        while True:
            with self._lock:
                now = self._time_fn()
                last = self._last_refill.get(key, now)
                tokens = min(self.capacity, self._tokens.get(key, self.capacity) + (now - last) * self.rate)
                self._last_refill[key] = now

                if tokens >= 1:
                    self._tokens[key] = tokens - 1
                    return

                self._tokens[key] = tokens
                wait = (1 - tokens) / self.rate

            self._sleep_fn(wait)


# Process-wide singleton so the bucket's state persists across requests --
# ExecutionEngine is instantiated fresh per request, but the throttling it
# enforces has to accumulate across requests to mean anything.
default_rate_limiter = TokenBucketRateLimiter(settings.BROKER_RATE_LIMIT_PER_SECOND)
