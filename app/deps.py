from fastapi import Query, Request

from app.store.memory_store import InMemoryStore


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_current_user_id(user_id: str = Query(..., description="Simple user identifier for this assignment's scope")) -> str:
    return user_id
