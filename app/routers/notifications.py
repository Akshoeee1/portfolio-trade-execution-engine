from fastapi import APIRouter, Depends

from app.deps import get_current_user_id, get_store
from app.schemas.notification import NotificationResponse
from app.store.memory_store import InMemoryStore

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    return [
        NotificationResponse(
            id=n.id,
            batch_id=n.batch_id,
            channel=n.channel,
            delivered=n.delivered,
            created_at=n.created_at,
            summary=n.summary,
        )
        for n in store.list_notifications(user_id)
    ]
