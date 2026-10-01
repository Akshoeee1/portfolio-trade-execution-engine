from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult


class GrowwAdapter(BrokerAdapter):
    """
    Stub adapter matching Groww's credential+TOTP login shape (assumption --
    Groww's public trading API, `growwapi`, is newer and less documented
    than the other 4 brokers'). Modeled as: API key + TOTP code exchanged
    for an access token, no browser redirect. Skipped here since it needs a
    live account to exercise for real.
    """

    broker_name = "groww"

    def get_login_url(self, **kwargs: Any) -> str | None:
        return None  # credential-based: no redirect, call authenticate() directly

    def authenticate(self, *, api_key: str, totp: str, **kwargs: Any) -> AuthSession:
        return AuthSession(access_token=f"stub-groww-token-{uuid4()}", extra={"stub": True})

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"STUB-GROWW-{uuid4()}",
            status="PLACED (stub)",
            raw_response={"stub": True, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="PLACED (stub)", raw_response={"stub": True})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
