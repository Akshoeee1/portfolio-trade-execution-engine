from enum import Enum

from pydantic import BaseModel, Field, model_validator


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    REBALANCE = "REBALANCE"


class TradeInstruction(BaseModel):
    symbol: str
    exchange: str = "NSE"
    broker: str
    action: TradeAction
    quantity: int = Field(gt=0)
    rebalance_direction: int | None = Field(
        default=None, description="+1 (add) or -1 (reduce); required when action == REBALANCE"
    )

    @model_validator(mode="after")
    def check_rebalance_direction(self) -> "TradeInstruction":
        if self.action == TradeAction.REBALANCE:
            if self.rebalance_direction not in (1, -1):
                raise ValueError("rebalance_direction must be 1 or -1 when action is REBALANCE")
        return self


class ExecutePortfolioRequest(BaseModel):
    instructions: list[TradeInstruction]


class OrderResult(BaseModel):
    symbol: str
    broker: str
    action: TradeAction
    quantity: int
    status: str
    broker_order_id: str | None
    error_message: str | None


class ExecutePortfolioResponse(BaseModel):
    batch_id: int
    status: str
    results: list[OrderResult]
