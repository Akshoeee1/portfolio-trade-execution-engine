from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.adapters.registry import BROKER_ADAPTERS
from app.deps import get_current_user_id, get_store
from app.schemas.broker import CallbackRequest, CallbackResponse, LoginUrlResponse
from app.services import auth_service
from app.services.simulated_login import render_login_page
from app.store.memory_store import InMemoryStore

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_broker(broker: str) -> None:
    if broker.lower() not in BROKER_ADAPTERS:
        raise HTTPException(status_code=404, detail=f"Unsupported broker: {broker}")


@router.get("/{broker}/login-url", response_model=LoginUrlResponse)
def login_url(broker: str, user_id: str = Depends(get_current_user_id)):
    _validate_broker(broker)
    url = auth_service.get_login_url(broker, user_id)
    return LoginUrlResponse(broker=broker, login_url=url)


@router.get("/{broker}/simulate-login", response_class=HTMLResponse)
def simulate_login(broker: str, user_id: str):
    _validate_broker(broker)
    return render_login_page(broker, user_id)


@router.post("/{broker}/callback", response_model=CallbackResponse)
def callback(
    broker: str,
    payload: CallbackRequest,
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    _validate_broker(broker)
    kwargs = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        auth_service.complete_login(store, user_id, broker, **kwargs)
    except TypeError as e:
        raise HTTPException(status_code=422, detail=f"Missing/invalid credentials for {broker}: {e}")
    return CallbackResponse(broker=broker, connected=True)
