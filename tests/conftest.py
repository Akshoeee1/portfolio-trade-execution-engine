import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.rate_limiter import default_rate_limiter
from app.store.memory_store import InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    fresh = InMemoryStore()
    app.state.store = fresh
    return fresh


@pytest.fixture
def client(store: InMemoryStore) -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_shared_rate_limiter():
    """
    The process-wide default_rate_limiter (app/services/rate_limiter.py)
    deliberately persists its token-bucket state across requests -- that's
    what makes it actually throttle anything in production. In a test
    process, that same persistence would otherwise leak real time.sleep()
    delays across unrelated tests (a token bucket drained by test A starts
    test B already short on tokens). Reset its state and swap in a no-op
    sleep before each test so tests stay fast and isolated; the limiter's
    own throttling behavior is covered directly in test_rate_limiter.py.
    """
    default_rate_limiter._tokens.clear()
    default_rate_limiter._last_refill.clear()
    original_sleep_fn = default_rate_limiter._sleep_fn
    default_rate_limiter._sleep_fn = lambda _seconds: None
    yield
    default_rate_limiter._sleep_fn = original_sleep_fn
