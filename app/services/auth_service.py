from app.adapters.base import AuthSession
from app.adapters.registry import get_adapter
from app.services import crypto_service
from app.store.memory_store import InMemoryStore
from app.store.models import BrokerConnection


def load_session(store: InMemoryStore, user_id: str, broker: str) -> AuthSession:
    connection = store.get_broker_connection(user_id, broker)
    if connection is None:
        raise ValueError(f"No {broker} connection found for user {user_id}. Authenticate first.")
    return AuthSession(
        access_token=crypto_service.decrypt(connection.encrypted_access_token),
        refresh_token=(
            crypto_service.decrypt(connection.encrypted_refresh_token)
            if connection.encrypted_refresh_token
            else None
        ),
        extra=connection.extra,
    )


def get_login_url(broker: str, user_id: str) -> str | None:
    adapter = get_adapter(broker)
    return adapter.get_login_url(user_id=user_id)


def complete_login(store: InMemoryStore, user_id: str, broker: str, **auth_kwargs) -> BrokerConnection:
    adapter = get_adapter(broker)
    session = adapter.authenticate(**auth_kwargs)

    connection = BrokerConnection(
        user_id=user_id,
        broker=broker,
        encrypted_access_token=crypto_service.encrypt(session.access_token),
        encrypted_refresh_token=(
            crypto_service.encrypt(session.refresh_token) if session.refresh_token else None
        ),
        extra=session.extra,
    )
    return store.upsert_broker_connection(connection)
