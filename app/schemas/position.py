from pydantic import BaseModel


class PositionsResponse(BaseModel):
    user_id: str
    positions: dict[str, dict[str, int]]  # { broker: { symbol: quantity } }
