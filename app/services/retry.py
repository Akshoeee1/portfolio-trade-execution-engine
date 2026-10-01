import time
from typing import Callable, TypeVar

from app.adapters.exceptions import RETRYABLE_BROKER_ERRORS, BrokerError

T = TypeVar("T")


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.3,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """
    Calls `fn()`, retrying with exponential backoff (base_delay * 2**attempt)
    only on exceptions in RETRYABLE_BROKER_ERRORS -- a rate limit or a
    transient connection blip is worth retrying; a broker's permanent
    rejection of the order (bad symbol, insufficient margin) is not, and
    is re-raised immediately on the first attempt.

    `sleep_fn` is injectable so tests can assert retry behavior without
    real delays.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except RETRYABLE_BROKER_ERRORS:
            if attempt >= max_attempts:
                raise
            sleep_fn(base_delay * (2 ** (attempt - 1)))
        except BrokerError:
            raise
