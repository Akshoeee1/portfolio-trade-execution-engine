import pytest
from fastapi.testclient import TestClient

from main import app
from app.store.memory_store import InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    fresh = InMemoryStore()
    app.state.store = fresh
    return fresh


@pytest.fixture
def client(store: InMemoryStore) -> TestClient:
    return TestClient(app)
