import pytest

from app.adapters.exceptions import BrokerAuthError, BrokerOrderRejectedError, BrokerRateLimitError
from app.services.retry import call_with_retry


def test_succeeds_immediately_without_retrying_when_no_error():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    sleeps: list[float] = []
    assert call_with_retry(fn, sleep_fn=sleeps.append) == "ok"
    assert calls["n"] == 1
    assert sleeps == []


def test_retries_on_rate_limit_then_succeeds():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise BrokerRateLimitError("too fast")
        return "ok"

    sleeps: list[float] = []
    result = call_with_retry(fn, max_attempts=5, base_delay=0.1, sleep_fn=sleeps.append)

    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.1, 0.2]  # exponential backoff: base_delay * 2**0, base_delay * 2**1


def test_gives_up_after_max_attempts():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise BrokerRateLimitError("still too fast")

    sleeps: list[float] = []
    with pytest.raises(BrokerRateLimitError):
        call_with_retry(fn, max_attempts=3, base_delay=0.1, sleep_fn=sleeps.append)

    assert calls["n"] == 3
    assert sleeps == [0.1, 0.2]


def test_does_not_retry_permanent_rejection():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise BrokerOrderRejectedError("bad symbol")

    sleeps: list[float] = []
    with pytest.raises(BrokerOrderRejectedError):
        call_with_retry(fn, max_attempts=5, sleep_fn=sleeps.append)

    assert calls["n"] == 1  # never retried
    assert sleeps == []


def test_does_not_retry_auth_error():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise BrokerAuthError("token expired")

    sleeps: list[float] = []
    with pytest.raises(BrokerAuthError):
        call_with_retry(fn, max_attempts=5, sleep_fn=sleeps.append)

    assert calls["n"] == 1
    assert sleeps == []
