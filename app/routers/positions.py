from fastapi import APIRouter, Depends

from app.deps import get_current_user_id, get_store
from app.schemas.position import PositionsResponse
from app.store.memory_store import InMemoryStore

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=PositionsResponse)
def get_positions(
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    """
    Net quantity held per broker/symbol, tracked from orders successfully
    placed through this system (NOT fetched from the broker's real
    holdings -- see app/services/execution_service.py for how this ledger
    gates SELL/REBALANCE-down orders).
    """
    return PositionsResponse(user_id=user_id, positions=store.list_positions(user_id))
