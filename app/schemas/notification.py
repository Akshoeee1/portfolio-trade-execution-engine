from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    batch_id: int
    channel: str
    delivered: bool
    created_at: datetime
    summary: dict
