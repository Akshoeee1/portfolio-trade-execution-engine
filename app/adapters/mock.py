from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult


class MockAdapter(BrokerAdapter):
    """No network calls. Used for tests and for demoing the engine end-to-end
    without any live broker account."""

    broker_name = "mock"

    def get_login_url(self, **kwargs: Any) -> str | None:
        return "https://mock-broker.example/login"

    def authenticate(self, **kwargs: Any) -> AuthSession:
        return AuthSession(access_token=f"mock-token-{uuid4()}", extra={"mock": True})

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"MOCK-{uuid4()}",
            status="PLACED",
            raw_response={
                "symbol": order.symbol,
                "action": order.action.value,
                "quantity": order.quantity,
            },
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="PLACED", raw_response={})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
