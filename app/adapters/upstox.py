from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult
from app.config import settings


class UpstoxAdapter(BrokerAdapter):
    """
    Stub adapter matching Upstox's real OAuth2 authorization-code flow.

    Real flow (not wired live here): browser login at
    https://api.upstox.com/v2/login/authorization/dialog with client_id +
    redirect_uri -> redirect carries `code` -> POST code + client_secret to
    https://api.upstox.com/v2/login/authorization/token for an access_token.
    The official `upstox-client` SDK implements this; skipped here for the
    same reason as Fyers -- avoid SDK-version fragility in an unwired stub.
    """

    broker_name = "upstox"
    AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"

    def get_login_url(self, **kwargs: Any) -> str | None:
        return (
            f"{self.AUTH_URL}?client_id={settings.UPSTOX_CLIENT_ID}"
            f"&redirect_uri={settings.UPSTOX_REDIRECT_URI}&response_type=code"
        )

    def authenticate(self, *, auth_code: str, **kwargs: Any) -> AuthSession:
        return AuthSession(access_token=f"stub-upstox-token-{uuid4()}", extra={"stub": True, "auth_code": auth_code})

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"STUB-UPSTOX-{uuid4()}",
            status="PLACED (stub)",
            raw_response={"stub": True, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="PLACED (stub)", raw_response={"stub": True})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
