from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult
from app.config import settings


class FyersAdapter(BrokerAdapter):
    """
    Stub adapter matching Fyers' real OAuth2 authcode-redirect shape.

    Real flow (not wired live here): browser login at
    https://api-t1.fyers.in/api/v3/generate-authcode with client_id +
    redirect_uri -> redirect carries `auth_code` -> POST auth_code plus
    app_id_hash (sha256 of "client_id:secret") to
    https://api-t1.fyers.in/api/v3/validate-authcode to get access_token.
    The official `fyers-apiv3` SDK implements this; skipped here to avoid
    SDK-version fragility for a stub that isn't exercised against a live
    account in this assignment.
    """

    broker_name = "fyers"
    AUTH_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"

    def get_login_url(self, **kwargs: Any) -> str | None:
        return (
            f"{self.AUTH_URL}?client_id={settings.FYERS_CLIENT_ID}"
            f"&redirect_uri={settings.FYERS_REDIRECT_URI}&response_type=code&state=sample"
        )

    def authenticate(self, *, auth_code: str, **kwargs: Any) -> AuthSession:
        return AuthSession(access_token=f"stub-fyers-token-{uuid4()}", extra={"stub": True, "auth_code": auth_code})

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"STUB-FYERS-{uuid4()}",
            status="PLACED (stub)",
            raw_response={"stub": True, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="PLACED (stub)", raw_response={"stub": True})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
