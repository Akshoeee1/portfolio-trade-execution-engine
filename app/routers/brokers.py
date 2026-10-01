from fastapi import APIRouter, Depends, HTTPException

from app.adapters.registry import BROKER_ADAPTERS, get_adapter
from app.deps import get_current_user_id, get_store
from app.schemas.broker import BrokerStatus, HoldingsResponse
from app.services.auth_service import load_session
from app.store.memory_store import InMemoryStore

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.get("", response_model=list[BrokerStatus])
def list_brokers(
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    return [
        BrokerStatus(broker=name, connected=store.get_broker_connection(user_id, name) is not None)
        for name in BROKER_ADAPTERS
    ]


@router.get("/{broker}/holdings", response_model=HoldingsResponse)
def holdings(
    broker: str,
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    if broker.lower() not in BROKER_ADAPTERS:
        raise HTTPException(status_code=404, detail=f"Unsupported broker: {broker}")
    try:
        session = load_session(store, user_id, broker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    adapter = get_adapter(broker)
    return HoldingsResponse(broker=broker, holdings=adapter.get_holdings(session))
