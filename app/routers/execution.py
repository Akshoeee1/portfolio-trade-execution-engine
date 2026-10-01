from fastapi import APIRouter, Depends

from app.deps import get_current_user_id, get_store
from app.schemas.trade import ExecutePortfolioRequest, ExecutePortfolioResponse, OrderResult
from app.services.execution_service import ExecutionEngine
from app.services.notification_service import NotificationService
from app.store.memory_store import InMemoryStore

router = APIRouter(tags=["execution"])


@router.post("/execute-portfolio", response_model=ExecutePortfolioResponse)
def execute_portfolio(
    payload: ExecutePortfolioRequest,
    user_id: str = Depends(get_current_user_id),
    store: InMemoryStore = Depends(get_store),
):
    engine = ExecutionEngine(store)
    batch = engine.execute(user_id, payload.instructions)
    orders = store.get_orders_for_batch(batch.id)

    NotificationService(store).notify_execution_complete(batch, orders)

    results = [
        OrderResult(
            symbol=o.symbol,
            broker=o.broker,
            action=o.action,
            quantity=o.quantity,
            status=o.status,
            broker_order_id=o.broker_order_id,
            error_message=o.error_message,
        )
        for o in orders
    ]
    return ExecutePortfolioResponse(batch_id=batch.id, status=batch.status, results=results)
